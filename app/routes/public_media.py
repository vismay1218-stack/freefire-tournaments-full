from flask import Blueprint

bp = Blueprint("public_media", __name__, url_prefix="/media")

from app.routes import public_media_routes  # noqa: E402,F401
