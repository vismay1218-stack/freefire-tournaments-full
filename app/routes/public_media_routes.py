from io import BytesIO
from mimetypes import guess_type

from flask import abort, current_app, send_file
from flask_login import current_user

from app.models.winner_proof import WinnerProof
from app.routes.public_media import bp
from app.services.upload_service import load_stored_image


@bp.route("/winners/<path:filename>")
def winner_image(filename):
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        abort(400)
    winner = WinnerProof.query.filter_by(image_path=filename).first()
    if winner is None or (not winner.published and not current_user.is_authenticated):
        abort(404)
    try:
        image = load_stored_image(filename, current_app.config, purpose="winner")
    except FileNotFoundError:
        abort(404)
    return send_file(
        BytesIO(image),
        mimetype=guess_type(filename)[0] or "application/octet-stream",
        download_name=filename,
        max_age=0,
    )
