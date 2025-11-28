from flask import Blueprint, jsonify
from flask_login import login_required

from database import get_db
from utils import role_required

api_bp = Blueprint("api", __name__)


@api_bp.route("/stats")
@login_required
@role_required("admin")
def stats():
    conn = get_db()
    totals = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM doctors) AS doctors,
            (SELECT COUNT(*) FROM patients) AS patients,
            (SELECT COUNT(*) FROM appointments) AS appointments
        """
    ).fetchone()
    return jsonify(
        {
            "doctors": totals["doctors"],
            "patients": totals["patients"],
            "appointments": totals["appointments"],
        }
    )


@api_bp.route("/doctor/<int:doctor_id>/appointments")
@login_required
@role_required("admin")
def doctor_appointments(doctor_id):
    conn = get_db()
    data = conn.execute(
        """
        SELECT id, date, time, status, patient_id
        FROM appointments
        WHERE doctor_id = ?
        ORDER BY date(date) DESC, time(time) DESC
        LIMIT 50
        """,
        (doctor_id,),
    ).fetchall()
    return jsonify([dict(row) for row in data])

