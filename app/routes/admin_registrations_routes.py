from datetime import datetime
from io import BytesIO
from mimetypes import guess_type
from flask import (
    render_template,
    abort,
    send_file,
    current_app,
    flash,
    redirect,
    url_for,
    request,
)
from app.routes.admin_registrations import bp
from app.auth.admin import login_required_admin
from app import db
from app.models.registration import Registration
from app.models.tournament import Tournament
from app.services.upload_service import load_stored_image


@bp.route("/admin/registrations")
@login_required_admin
def list_():
    status_filter = request.args.get("filter", "all").lower()
    tournament_id = request.args.get("tournament_id", type=int)

    query = Registration.query.options(
        db.joinedload(Registration.tournament),
        db.joinedload(Registration.players),
    )

    if status_filter == "pending":
        query = query.filter(Registration.registration_status == "PENDING_PAYMENT_VERIFICATION")
    elif status_filter == "confirmed":
        query = query.filter(Registration.registration_status == "CONFIRMED")
    elif status_filter == "rejected":
        query = query.filter(Registration.registration_status == "REJECTED")

    if tournament_id:
        query = query.filter(Registration.tournament_id == tournament_id)

    registrations = query.order_by(Registration.created_at.desc()).all()
    return render_template(
        "admin/registrations/list.html",
        registrations=registrations,
        status_filter=status_filter,
        tournament_id=tournament_id,
    )


@bp.route("/admin/registrations/<int:registration_id>")
@login_required_admin
def view(registration_id):
    registration = db.get_or_404(Registration, registration_id)
    return render_template("admin/registrations/view.html", registration=registration)


@bp.route("/admin/registrations/<int:registration_id>/approve", methods=["POST"])
@login_required_admin
def approve(registration_id):
    registration = db.get_or_404(Registration, registration_id)
    if registration.registration_status == "CONFIRMED":
        flash("Registration is already confirmed.", "info")
        return redirect(request.referrer or url_for("admin_registrations.list_"))

    tournament = registration.tournament
    if tournament and tournament.confirmed_count >= tournament.max_teams:
        flash(
            f"Cannot approve: Tournament '{tournament.name}' is already full ({tournament.max_teams} teams reached).",
            "danger",
        )
        return redirect(request.referrer or url_for("admin_registrations.list_"))

    registration.registration_status = "CONFIRMED"
    registration.payment_status = "VERIFIED"
    registration.confirmation_date = datetime.utcnow()
    if not registration.registration_id:
        registration.registration_id = f"PV-{registration.id:04d}"

    db.session.commit()
    flash(
        f"Registration for team '{registration.team_name}' approved successfully! Assigned Team ID: {registration.registration_id}",
        "success",
    )
    return redirect(request.referrer or url_for("admin_registrations.list_"))


@bp.route("/admin/registrations/<int:registration_id>/reject", methods=["POST"])
@login_required_admin
def reject(registration_id):
    registration = db.get_or_404(Registration, registration_id)
    rejection_reason = (request.form.get("rejection_reason") or "Payment could not be verified.").strip()

    registration.registration_status = "REJECTED"
    registration.payment_status = "FAILED"
    registration.rejection_reason = rejection_reason

    db.session.commit()
    flash(f"Registration for team '{registration.team_name}' rejected.", "warning")
    return redirect(request.referrer or url_for("admin_registrations.list_"))


@bp.route("/api/admin/screenshots/<path:filename>")
@login_required_admin
def serve_screenshot(filename):
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        abort(400)
    try:
        image = load_stored_image(filename, current_app.config, purpose="payment")
    except FileNotFoundError:
        abort(404)
    return send_file(
        BytesIO(image),
        mimetype=guess_type(filename)[0] or "application/octet-stream",
        download_name=filename,
        max_age=0,
    )
