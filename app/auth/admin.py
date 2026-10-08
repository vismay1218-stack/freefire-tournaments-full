from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def login_required_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("admin_auth.login"))
        return fn(*args, **kwargs)
    return wrapper
