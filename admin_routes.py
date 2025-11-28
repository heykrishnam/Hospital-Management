from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required
from werkzeug.security import generate_password_hash

from database import get_db
from utils import role_required
from models import fetch_user_by_username

admin_bp = Blueprint("admin", __name__, template_folder="templates/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    conn = get_db()
    totals = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM doctors) AS doctors,
            (SELECT COUNT(*) FROM patients) AS patients,
            (SELECT COUNT(*) FROM appointments) AS appointments
        """
    ).fetchone()

    upcoming = conn.execute(
        """
        SELECT a.*, p.full_name AS patient_name, d.full_name AS doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        WHERE date(a.date) >= date('now')
        ORDER BY a.date, a.time
        LIMIT 5
        """
    ).fetchall()

    return render_template("admin/dashboard.html", totals=totals, upcoming=upcoming)


@admin_bp.route("/doctors", methods=["GET", "POST"])
@login_required
@role_required("admin")
def doctors():
    conn = get_db()

    if request.method == "POST" and request.form.get("dept_name"):
        name = request.form.get("dept_name")
        desc = request.form.get("dept_desc")
        conn.execute(
            "INSERT OR IGNORE INTO departments (name, description) VALUES (?, ?)",
            (name, desc),
        )
        conn.commit()
        flash("Department saved.", "success")
        return redirect(url_for("admin.doctors"))

    doctors = conn.execute(
        """
        SELECT d.*, u.email, dept.name AS department_name
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.department_id = dept.id
        ORDER BY d.full_name
        """
    ).fetchall()
    departments = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()

    return render_template(
        "admin/doctors.html", doctors=doctors, departments=departments
    )


@admin_bp.route("/add_doctor", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_doctor():
    conn = get_db()
    departments = conn.execute("SELECT * FROM departments").fetchall()

    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password")
        full_name = request.form.get("full_name")
        specialization = request.form.get("specialization")
        department_id = request.form.get("department_id")

        if fetch_user_by_username(username):
            flash("Username already exists.", "danger")
            return redirect(url_for("admin.add_doctor"))

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'doctor')",
            (username, email, generate_password_hash(password)),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO doctors (user_id, full_name, specialization, department_id)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, full_name, specialization, department_id),
        )
        conn.commit()
        flash("Doctor added.", "success")
        return redirect(url_for("admin.doctors"))

    return render_template("admin/add_doctor.html", departments=departments)


@admin_bp.route("/edit_doctor/<int:doctor_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_doctor(doctor_id):
    conn = get_db()
    doctor = conn.execute(
        """
        SELECT d.*, u.email, u.username
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        WHERE d.id = ?
        """,
        (doctor_id,),
    ).fetchone()
    departments = conn.execute("SELECT * FROM departments").fetchall()

    if not doctor:
        flash("Doctor not found.", "warning")
        return redirect(url_for("admin.doctors"))

    if request.method == "POST":
        full_name = request.form.get("full_name")
        specialization = request.form.get("specialization")
        department_id = request.form.get("department_id")
        is_blacklisted = 1 if request.form.get("is_blacklisted") == "on" else 0

        conn.execute(
            """
            UPDATE doctors
            SET full_name=?, specialization=?, department_id=?, is_blacklisted=?
            WHERE id=?
            """,
            (full_name, specialization, department_id, is_blacklisted, doctor_id),
        )
        conn.commit()
        flash("Doctor updated.", "success")
        return redirect(url_for("admin.doctors"))

    return render_template(
        "admin/edit_doctor.html", doctor=doctor, departments=departments
    )


@admin_bp.route("/delete_doctor/<int:doctor_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_doctor(doctor_id):
    conn = get_db()
    doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    if not doctor:
        flash("Doctor not found.", "warning")
        return redirect(url_for("admin.doctors"))

    conn.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (doctor["user_id"],))
    conn.commit()
    flash("Doctor deleted.", "info")
    return redirect(url_for("admin.doctors"))


@admin_bp.route("/search")
@login_required
@role_required("admin")
def search():
    query = request.args.get("q", "")
    scope = request.args.get("scope", "doctor")
    conn = get_db()
    doctors = patients = []

    if scope == "doctor":
        doctors = conn.execute(
            """
            SELECT d.*, dept.name AS department_name
            FROM doctors d
            LEFT JOIN departments dept ON d.department_id = dept.id
            WHERE d.full_name LIKE ? OR d.specialization LIKE ?
            """,
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        patients = conn.execute(
            """
            SELECT * FROM patients
            WHERE full_name LIKE ? OR contact LIKE ? OR CAST(id AS TEXT) LIKE ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()

    return render_template(
        "admin/search.html", query=query, scope=scope, doctors=doctors, patients=patients
    )


@admin_bp.route("/appointments")
@login_required
@role_required("admin")
def appointments():
    conn = get_db()
    data = conn.execute(
        """
        SELECT a.*, p.full_name AS patient_name, d.full_name AS doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY date(a.date) DESC, time(a.time) DESC
        """
    ).fetchall()
    return render_template("admin/appointments.html", appointments=data)

