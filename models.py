from flask_login import UserMixin
from flask import current_app
from database import get_db


class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role


def fetch_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return user


def fetch_user_by_username(username):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return user


def fetch_patient_by_user(user_id):
    conn = get_db()
    return conn.execute(
        "SELECT * FROM patients WHERE user_id = ?", (user_id,)
    ).fetchone()


def fetch_doctor_by_user(user_id):
    conn = get_db()
    return conn.execute(
        "SELECT * FROM doctors WHERE user_id = ?", (user_id,)
    ).fetchone()

