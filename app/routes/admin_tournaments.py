from flask import Blueprint

bp = Blueprint("admin_tournaments", __name__, url_prefix="", template_folder="templates")

from app.routes import admin_tournaments_routes  # noqa: E402,F401
