# Hospital Management System (Flask)

## Stack
- Flask + Flask-Login
- SQLite (auto-created)
- Bootstrap 5 + custom CSS

## Quickstart
```bash
cd hms
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py
```
Navigate to `http://127.0.0.1:5000`.

### Default Admin
- user: `admin`
- pass: `Admin@123`

## ER Diagram (text)
```
users (1) ──┐
            ├─> doctors (0..1) ──> appointments (0..*) ──> treatments (0..1)
            └─> patients (0..1) ───────┘

departments (1) ──< doctors
```

## Key Features
- Role-based dashboards (Admin / Doctor / Patient)
- Patient self-registration + profile management
- Doctor management (CRUD, blacklist, departments)
- Appointment scheduling with conflict prevention
- Doctor availability window (next 7 days)
- Treatment capture + complete medical history
- Search doctors and patients
- Bootstrap UI with template inheritance
- Optional JSON API (`/api/stats`, `/api/doctor/<id>/appointments`) for integration

## Project Layout
```
hms/
  app.py                # Flask app + blueprint wiring
  database.py           # SQLite creation + teardown helpers
  auth_routes.py        # Login, logout, registration
  admin_routes.py       # Admin dashboard & management
  doctor_routes.py      # Doctor views, availability, treatments
  patient_routes.py     # Patient dashboard, booking, history
  models.py             # Shared fetch helpers
  utils.py              # Role-based decorator
  api_routes.py         # Lightweight JSON endpoints (admin-protected)
  templates/            # Jinja2 views (base + per-role)
  static/css/style.css  # Custom styling
  requirements.txt
```

## Optional Enhancements
- Add REST API views for mobile apps
- Plug in email/SMS reminders
- Expand appointment reschedule UI with dropdowns based on availability JSON

