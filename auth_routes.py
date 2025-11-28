from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db
from models import User, fetch_user_by_username

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(f"{current_user.role}.dashboard"))

    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")

        conn = get_db()
        user_row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user_row and check_password_hash(user_row["password_hash"], password):
            user = User(user_row["id"], user_row["username"], user_row["role"])
            login_user(user)
            flash("Login successful.", "success")
            return redirect(url_for(f"{user.role}.dashboard"))

        flash("Invalid credentials.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password")
        full_name = request.form.get("full_name")
        age = request.form.get("age")
        gender = request.form.get("gender")
        contact = request.form.get("contact")

        if fetch_user_by_username(username):
            flash("Username already exists.", "danger")
            return redirect(url_for("auth.register"))

        conn = get_db()
        password_hash = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'patient')",
            (username, email, password_hash),
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO patients (user_id, full_name, age, gender, contact)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, full_name, age, gender, contact),
        )
        conn.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

