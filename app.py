import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user

from database import init_db, close_db
from models import User, fetch_user_by_id


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "super-secure-hms-key"
    app.config["DATABASE"] = os.path.join(os.path.dirname(__file__), "hms.db")

    # Ensure the instance path exists for SQLite file placement
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    init_db(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        row = fetch_user_by_id(user_id)
        if row:
            return User(row["id"], row["username"], row["role"])
        return None

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for(f"{current_user.role}.dashboard"))
        return redirect(url_for("auth.login"))

    # Register blueprints
    from auth_routes import auth_bp
    from admin_routes import admin_bp
    from doctor_routes import doctor_bp
    from patient_routes import patient_bp
    from api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(patient_bp, url_prefix="/patient")
    app.register_blueprint(api_bp, url_prefix="/api")

    app.teardown_appcontext(close_db)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

