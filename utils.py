from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if current_user.role != role:
                flash("Unauthorized access.", "danger")
                return redirect(url_for(f"{current_user.role}.dashboard"))
            return func(*args, **kwargs)

        return wrapper

    return decorator

