from flask import Blueprint

bp = Blueprint("admin_auth", __name__, url_prefix="", template_folder="templates")

from app.routes import admin_auth_routes  # noqa: E402,F401
