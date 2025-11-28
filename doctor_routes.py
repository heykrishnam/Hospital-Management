import json
from datetime import datetime, timedelta
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
from models import fetch_doctor_by_user

doctor_bp = Blueprint("doctor", __name__)


def get_doctor():
    doctor = fetch_doctor_by_user(current_user.id)
    if not doctor:
        flash("Doctor profile not found. Contact admin.", "danger")
        return None
    return doctor


def load_availability(doc_row):
    if not doc_row["availability"]:
        return {}
    try:
        return json.loads(doc_row["availability"])
    except json.JSONDecodeError:
        return {}


@doctor_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def dashboard():
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()

    week_dates = [
        (datetime.utcnow().date() + timedelta(days=i)).isoformat() for i in range(7)
    ]

    if request.method == "POST":
        availability = {}
        for day in week_dates:
            slot_string = request.form.get(f"slot_{day}", "")
            slots = [s.strip() for s in slot_string.split(",") if s.strip()]
            if slots:
                availability[day] = slots
        conn.execute(
            "UPDATE doctors SET availability = ? WHERE id = ?",
            (json.dumps(availability), doctor["id"]),
        )
        conn.commit()
        flash("Availability updated.", "success")
        return redirect(url_for("doctor.dashboard"))

    availability = load_availability(doctor)
    upcoming = conn.execute(
        """
        SELECT a.*, p.full_name AS patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ? AND date(a.date) >= date('now')
        ORDER BY a.date, a.time
        LIMIT 10
        """,
        (doctor["id"],),
    ).fetchall()

    week_end = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    weekly = conn.execute(
        """
        SELECT a.*, p.full_name AS patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
          AND date(a.date) BETWEEN date('now') AND date(?)
        ORDER BY a.date, a.time
        """,
        (doctor["id"], week_end),
    ).fetchall()

    return render_template(
        "doctor/dashboard.html",
        doctor=doctor,
        availability=availability,
        upcoming=upcoming,
        weekly=weekly,
        week_dates=week_dates,
    )


@doctor_bp.route("/appointments")
@login_required
@role_required("doctor")
def appointments():
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    status_filter = request.args.get("status")
    query = """
        SELECT a.*, p.full_name AS patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ?
    """
    params = [doctor["id"]]
    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)
    query += " ORDER BY date(a.date) DESC, time(a.time) DESC"

    items = conn.execute(query, params).fetchall()
    return render_template("doctor/appointments.html", appointments=items)


@doctor_bp.route("/complete/<int:appointment_id>", methods=["POST"])
@login_required
@role_required("doctor")
def mark_complete(appointment_id):
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    conn.execute(
        """
        UPDATE appointments
        SET status = 'Completed'
        WHERE id = ? AND doctor_id = ?
        """,
        (appointment_id, doctor["id"]),
    )
    conn.commit()
    flash("Appointment marked as completed. Add treatment details.", "info")
    return redirect(url_for("doctor.update_treatment", appointment_id=appointment_id))


@doctor_bp.route("/update_treatment/<int:appointment_id>", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def update_treatment(appointment_id):
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    appointment = conn.execute(
        """
        SELECT a.*, p.full_name AS patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ? AND a.doctor_id = ?
        """,
        (appointment_id, doctor["id"]),
    ).fetchone()

    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("doctor.appointments"))

    treatment = conn.execute(
        "SELECT * FROM treatments WHERE appointment_id = ?", (appointment_id,)
    ).fetchone()

    if request.method == "POST":
        diagnosis = request.form.get("diagnosis")
        prescription = request.form.get("prescription")
        notes = request.form.get("notes")
        if treatment:
            conn.execute(
                """
                UPDATE treatments
                SET diagnosis=?, prescription=?, notes=?
                WHERE appointment_id=?
                """,
                (diagnosis, prescription, notes, appointment_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO treatments (appointment_id, diagnosis, prescription, notes)
                VALUES (?, ?, ?, ?)
                """,
                (appointment_id, diagnosis, prescription, notes),
            )
        conn.commit()
        flash("Treatment record saved.", "success")
        return redirect(url_for("doctor.appointments"))

    return render_template(
        "doctor/update_treatment.html",
        appointment=appointment,
        treatment=treatment,
    )


@doctor_bp.route("/patient_history/<int:patient_id>")
@login_required
@role_required("doctor")
def patient_history(patient_id):
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    patient = conn.execute(
        "SELECT * FROM patients WHERE id = ?", (patient_id,)
    ).fetchone()
    if not patient:
        flash("Patient not found.", "warning")
        return redirect(url_for("doctor.appointments"))

    treatments = conn.execute(
        """
        SELECT a.date, a.time, a.status, t.diagnosis, t.prescription, t.notes
        FROM appointments a
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ?
        ORDER BY date(a.date) DESC
        """,
        (patient_id,),
    ).fetchall()

    return render_template(
        "doctor/patient_history.html", patient=patient, treatments=treatments
    )


@doctor_bp.route("/pending/<int:appointment_id>/approve", methods=["POST"])
@login_required
@role_required("doctor")
def approve_pending(appointment_id):
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    cursor = conn.execute(
        """
        UPDATE appointments
        SET status='Booked'
        WHERE id=? AND doctor_id=? AND status='PendingApproval'
        """,
        (appointment_id, doctor["id"]),
    )
    conn.commit()

    if cursor.rowcount:
        flash("Appointment approved and confirmed.", "success")
    else:
        flash("Unable to approve appointment.", "warning")
    return redirect(url_for("doctor.appointments"))


@doctor_bp.route("/pending/<int:appointment_id>/reject", methods=["POST"])
@login_required
@role_required("doctor")
def reject_pending(appointment_id):
    doctor = get_doctor()
    if not doctor:
        return redirect(url_for("auth.logout"))

    conn = get_db()
    cursor = conn.execute(
        """
        UPDATE appointments
        SET status='Cancelled'
        WHERE id=? AND doctor_id=? AND status='PendingApproval'
        """,
        (appointment_id, doctor["id"]),
    )
    conn.commit()

    if cursor.rowcount:
        flash("Appointment request declined.", "info")
    else:
        flash("Unable to update appointment.", "warning")
    return redirect(url_for("doctor.appointments"))

