import json
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user

from database import get_db
from utils import role_required
from models import fetch_patient_by_user

patient_bp = Blueprint("patient", __name__)


def get_patient():
    patient = fetch_patient_by_user(current_user.id)
    if not patient:
        flash("Patient profile not found. Please complete registration.", "danger")
    return patient


@patient_bp.route("/dashboard")
@login_required
@role_required("patient")
def dashboard():
    patient = get_patient()
    if not patient:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    departments = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()
    upcoming = conn.execute(
        """
        SELECT a.*, d.full_name AS doctor_name, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ? AND date(a.date) >= date('now')
        ORDER BY a.date, a.time
        """,
        (patient["id"],),
    ).fetchall()

    history = conn.execute(
        """
        SELECT a.*, d.full_name AS doctor_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ? AND date(a.date) < date('now')
        ORDER BY a.date DESC
        LIMIT 5
        """,
        (patient["id"],),
    ).fetchall()

    return render_template(
        "patient/dashboard.html",
        patient=patient,
        departments=departments,
        upcoming=upcoming,
        history=history,
    )


@patient_bp.route("/search_doctor")
@login_required
@role_required("patient")
def search_doctor():
    conn = get_db()
    specialization = request.args.get("specialization", "")
    doctors = conn.execute(
        """
        SELECT d.*, dept.name AS department_name
        FROM doctors d
        LEFT JOIN departments dept ON d.department_id = dept.id
        WHERE d.is_blacklisted = 0
          AND (d.specialization LIKE ? OR dept.name LIKE ?)
        ORDER BY d.full_name
        """,
        (f"%{specialization}%", f"%{specialization}%"),
    ).fetchall()
    return render_template(
        "patient/search_doctor.html", doctors=doctors, specialization=specialization
    )


@patient_bp.route("/book/<int:doctor_id>", methods=["GET", "POST"])
@login_required
@role_required("patient")
def book(doctor_id):
    patient = get_patient()
    if not patient:
        return redirect(url_for("patient.dashboard"))

    conn = get_db()
    doctor = conn.execute(
        """
        SELECT d.*, u.email
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        WHERE d.id = ? AND d.is_blacklisted = 0
        """,
        (doctor_id,),
    ).fetchone()
    if not doctor:
        flash("Doctor not found or unavailable.", "warning")
        return redirect(url_for("patient.search_doctor"))

    availability = {}
    if doctor["availability"]:
        try:
            availability = json.loads(doctor["availability"])
        except json.JSONDecodeError:
            availability = {}

    pending_choice = None
    selected_date = None
    selected_time = None

    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")
        appointment_id = request.form.get("appointment_id")
        confirm_pending = request.form.get("confirm_pending")
        selected_date, selected_time = date, time

        has_defined_slots = bool(availability)
        slot_in_schedule = (
            not has_defined_slots
            or (date in availability and time in availability.get(date, []))
        )

        conflict = conn.execute(
            """
            SELECT 1 FROM appointments
            WHERE doctor_id = ? AND date = ? AND time = ? AND status != 'Cancelled'
            """,
            (doctor_id, date, time),
        ).fetchone()

        needs_approval = False
        pending_reason = ""
        if not slot_in_schedule and has_defined_slots:
            needs_approval = True
            pending_reason = "Selected time is outside the doctor's published availability."
        elif conflict:
            needs_approval = True
            pending_reason = "Selected slot is already booked."

        if needs_approval:
            if confirm_pending == "yes":
                if appointment_id:
                    conn.execute(
                        """
                        UPDATE appointments
                        SET date=?, time=?, status='PendingApproval'
                        WHERE id=? AND patient_id=?
                        """,
                        (date, time, appointment_id, patient["id"]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO appointments (patient_id, doctor_id, date, time, status)
                        VALUES (?, ?, ?, ?, 'PendingApproval')
                        """,
                        (patient["id"], doctor_id, date, time),
                    )
                conn.commit()
                flash("Approval request sent to doctor.", "info")
                return redirect(url_for("patient.dashboard"))

            flash(
                "Slot is not available. Do you want to request doctor approval?",
                "warning",
            )
            pending_choice = {
                "date": date,
                "time": time,
                "appointment_id": appointment_id or "",
                "reason": pending_reason,
            }
        else:
            if appointment_id:
                conn.execute(
                    """
                    UPDATE appointments
                    SET date=?, time=?, status='Booked'
                    WHERE id=? AND patient_id=?
                    """,
                    (date, time, appointment_id, patient["id"]),
                )
                flash("Appointment rescheduled.", "success")
            else:
                conn.execute(
                    """
                    INSERT INTO appointments (patient_id, doctor_id, date, time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (patient["id"], doctor_id, date, time),
                )
                flash("Appointment booked.", "success")
            conn.commit()
            return redirect(url_for("patient.dashboard"))

    return render_template(
        "patient/book.html",
        doctor=doctor,
        availability=availability,
        pending_choice=pending_choice,
        selected_date=selected_date,
        selected_time=selected_time,
    )


@patient_bp.route("/cancel/<int:appointment_id>", methods=["POST"])
@login_required
@role_required("patient")
def cancel(appointment_id):
    patient = get_patient()
    if not patient:
        return redirect(url_for("patient.dashboard"))

    conn = get_db()
    conn.execute(
        """
        UPDATE appointments SET status='Cancelled'
        WHERE id=? AND patient_id=?
        """,
        (appointment_id, patient["id"]),
    )
    conn.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("patient.dashboard"))


@patient_bp.route("/history")
@login_required
@role_required("patient")
def history():
    patient = get_patient()
    if not patient:
        return redirect(url_for("patient.dashboard"))

    conn = get_db()
    records = conn.execute(
        """
        SELECT a.*, d.full_name AS doctor_name, t.diagnosis, t.prescription
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ?
        ORDER BY date(a.date) DESC
        """,
        (patient["id"],),
    ).fetchall()

    return render_template("patient/history.html", appointments=records)


@patient_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("patient")
def profile():
    patient = get_patient()
    if not patient:
        return redirect(url_for("patient.dashboard"))

    conn = get_db()
    if request.method == "POST":
        full_name = request.form.get("full_name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        contact = request.form.get("contact")
        address = request.form.get("address")
        blood = request.form.get("blood_group")
        emergency = request.form.get("emergency_contact")
        conn.execute(
            """
            UPDATE patients
            SET full_name=?, age=?, gender=?, contact=?, address=?, blood_group=?, emergency_contact=?
            WHERE id=?
            """,
            (full_name, age, gender, contact, address, blood, emergency, patient["id"]),
        )
        conn.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("patient.profile"))

    return render_template("patient/profile.html", patient=patient)

