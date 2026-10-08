from flask import Blueprint

bp = Blueprint("admin_winners", __name__, url_prefix="", template_folder="templates")

from app.routes import admin_winners_routes  # noqa: E402,F401
