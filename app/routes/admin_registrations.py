from flask import Blueprint

bp = Blueprint("admin_registrations", __name__, url_prefix="", template_folder="templates")

from app.routes import admin_registrations_routes  # noqa: E402,F401
