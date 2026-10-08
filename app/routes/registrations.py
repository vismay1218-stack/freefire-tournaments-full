from flask import Blueprint

bp = Blueprint("registrations", __name__, url_prefix="")

from app.routes import registrations_routes  # noqa: E402,F401
