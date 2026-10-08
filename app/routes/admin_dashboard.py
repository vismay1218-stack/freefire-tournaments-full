from flask import Blueprint

bp = Blueprint("admin_dashboard", __name__, url_prefix="", template_folder="templates")

from app.routes import admin_dashboard_routes  # noqa: E402,F401
