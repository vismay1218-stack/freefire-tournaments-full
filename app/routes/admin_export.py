from flask import Blueprint

bp = Blueprint("admin_export", __name__, url_prefix="", template_folder="templates")

from app.routes import admin_export_routes  # noqa: E402,F401
