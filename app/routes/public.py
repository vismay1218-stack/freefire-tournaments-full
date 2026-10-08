from flask import Blueprint

bp = Blueprint("public", __name__, url_prefix="", template_folder="templates")

from app.routes import public_routes  # noqa: E402,F401
