from datetime import datetime
from flask import abort, request, send_file
from app.routes.admin_export import bp
from app.auth.admin import login_required_admin
from app import db
from app.models.tournament import Tournament
from app.models.registration import Registration
from app.services.excel_service import generate_registrations_export
from werkzeug.utils import secure_filename


@bp.route("/admin/export/excel")
@bp.route("/api/admin/export/excel")
@login_required_admin
def excel():
    status_filter = request.args.get("filter", "all").lower()
    tournament_id = request.args.get("tournament_id", type=int)
    tournament = db.session.get(Tournament, tournament_id) if tournament_id else None
    if tournament_id and tournament is None:
        abort(404)

    query = Registration.query.options(
        db.joinedload(Registration.tournament),
        db.joinedload(Registration.players),
    )

    if status_filter == "confirmed":
        query = query.filter(Registration.registration_status == "CONFIRMED")
    elif status_filter == "pending":
        query = query.filter(Registration.registration_status == "PENDING_PAYMENT_VERIFICATION")
    elif status_filter == "rejected":
        query = query.filter(Registration.registration_status == "REJECTED")

    if tournament:
        query = query.filter(Registration.tournament_id == tournament_id)

    registrations = query.order_by(Registration.created_at.desc()).all()

    excel_file = generate_registrations_export(registrations)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    tournament_prefix = (
        f"{secure_filename(tournament.name)}_" if tournament else ""
    )
    filename = f"registrations_{tournament_prefix}{status_filter}_{timestamp}.xlsx"

    return send_file(
        excel_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
