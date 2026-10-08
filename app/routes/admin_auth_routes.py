from flask import render_template, redirect, request, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from app import db, limiter
from app.models.admin import Admin
from app.routes.admin_auth import bp
from app.auth.admin import login_required_admin


@bp.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = Admin.query.filter(Admin.email == email).first()
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin, remember=False)
            return redirect(url_for("admin_dashboard.index"))
        flash("Invalid email or password.", "danger")
    return render_template("admin/login.html"), 200


@bp.route("/admin/logout", methods=["POST"])
@login_required_admin
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_auth.login"))


@bp.route("/api/admin/me")
def admin_me():
    if not current_user.is_authenticated:
        return jsonify({"error": "unauthenticated"}), 401
    return jsonify({"email": current_user.email, "id": current_user.id})
