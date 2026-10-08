import os
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "admin_auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


def ensure_dirs(config):
    for d in [
        config["UPLOAD_FOLDER"],
        config["PAYMENT_SCREENSHOTS_DIR"],
        config["WINNERS_PUBLIC_DIR"],
        config["EXPORTS_DIR"],
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)
        gitkeep = Path(d) / ".gitkeep"
        if not gitkeep.exists():
            try:
                gitkeep.touch()
            except OSError:
                pass


def register_blueprints(app):
    from app.routes.admin_auth import bp as admin_auth_bp
    from app.routes.admin_dashboard import bp as admin_dashboard_bp
    from app.routes.admin_tournaments import bp as admin_tournaments_bp
    from app.routes.admin_registrations import bp as admin_registrations_bp
    from app.routes.admin_winners import bp as admin_winners_bp
    from app.routes.admin_export import bp as admin_export_bp
    from app.routes.public import bp as public_bp
    from app.routes.registrations import bp as registrations_bp
    from app.routes.public_media import bp as public_media_bp

    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(admin_tournaments_bp)
    app.register_blueprint(admin_registrations_bp)
    app.register_blueprint(admin_winners_bp)
    app.register_blueprint(admin_export_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(registrations_bp)
    app.register_blueprint(public_media_bp)


def register_error_handlers(app):
    from flask import render_template, jsonify

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        import logging
        logging.exception("500 error: %s", e)
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"errors": {"_general": "Uploaded file is too large."}}), 413


def register_template_helpers(app):
    @app.template_filter("currency")
    def currency_fmt(value):
        try:
            return f"₹{int(value):,}"
        except (TypeError, ValueError):
            return f"₹{value}"


def register_cli(app):
    from app.cli import register_cli
    register_cli(app)


def create_app(config_object=None):
    from config import Config as DefaultConfig

    if config_object is None:
        config_object = DefaultConfig

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent / "static"),
    )
    app.config.from_object(config_object)
    app.config["BASE_DIR"] = Path(__file__).resolve().parent.parent

    if os.getenv("VERCEL"):
        required = (
            "SECRET_KEY",
            "DATABASE_URL",
            "ADMIN_EMAIL",
            "ADMIN_PASSWORD",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
        )
        missing = [key for key in required if not app.config.get(key)]
        if missing:
            raise RuntimeError(
                "Missing required Vercel environment variables: "
                + ", ".join(missing)
            )
        if app.config["DATABASE_URL"].startswith("sqlite:"):
            raise RuntimeError("Vercel deployments require a persistent PostgreSQL database.")

    ensure_dirs(app.config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.models.admin import Admin
    from werkzeug.security import generate_password_hash

    @login_manager.user_loader
    def load_admin(user_id):
        return db.session.get(Admin, int(user_id))

    register_blueprints(app)
    register_error_handlers(app)
    register_template_helpers(app)
    register_cli(app)

    # Initialize tables and provision the configured admin account.
    with app.app_context():
        db.create_all()
        email = (app.config.get("ADMIN_EMAIL") or "").strip().lower()
        password = app.config.get("ADMIN_PASSWORD") or ""
        if bool(email) != bool(password):
            raise RuntimeError("Set both ADMIN_EMAIL and ADMIN_PASSWORD, or leave both empty.")
        if email and password:
            existing = Admin.query.filter_by(email=email).first()
            if existing is None:
                db.session.add(
                    Admin(email=email, password_hash=generate_password_hash(password))
                )
            else:
                existing.password_hash = generate_password_hash(password)
            db.session.commit()

    return app
