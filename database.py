import sqlite3
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin','doctor','patient'))
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                department_id INTEGER,
                specialization TEXT NOT NULL,
                availability TEXT DEFAULT '',
                is_blacklisted INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (department_id) REFERENCES departments(id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                contact TEXT,
                address TEXT,
                blood_group TEXT,
                emergency_contact TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Booked',
                UNIQUE(doctor_id, date, time),
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS treatments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER UNIQUE NOT NULL,
                diagnosis TEXT,
                prescription TEXT,
                notes TEXT,
                FOREIGN KEY (appointment_id) REFERENCES appointments(id)
            );
            """
        )

        # Seed default departments
        cursor.executemany(
            "INSERT OR IGNORE INTO departments (name, description) VALUES (?, ?)",
            [
                ("Cardiology", "Heart and blood vessel specialists"),
                ("Neurology", "Brain and nervous system"),
                ("Pediatrics", "Child healthcare"),
                ("Orthopedics", "Bone and muscle care"),
            ],
        )

        # Seed admin user
        admin_username = "admin"
        admin_email = "admin@hms.local"
        admin_password = generate_password_hash("Admin@123")
        cursor.execute(
            """
            INSERT OR IGNORE INTO users (id, username, email, password_hash, role)
            VALUES (1, ?, ?, ?, 'admin')
            """,
            (admin_username, admin_email, admin_password),
        )

        conn.commit()

