from datetime import datetime

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.player import Player
from app.models.registration import Registration
from app.models.tournament import Tournament
from app.routes.registrations import bp
from app.services.upload_service import save_payment_screenshot


INVALID_UID_MSG = "Player {idx} UID is invalid. Please enter a valid Free Fire UID."
INVALID_LEVEL_MSG = "Player {idx} level must be more than 30. Current level: {val}."
PHONE_REGEX = None


def _is_valid_phone(v: str) -> bool:
    import re
    return bool(re.fullmatch(r"[6-9]\d{9}", v or ""))


def _is_valid_uid(v: str) -> bool:
    import re
    return bool(re.fullmatch(r"\d{9,12}", v or ""))


def _is_valid_level(v) -> bool:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return False
    return isinstance(n, int) and n > 30


def _formval(name):
    return (request.form.get(name) or "").strip()


def _validate_registration(tournament):
    errors = {}

    team_name = _formval("team_name")
    captain_name = _formval("captain_name")
    captain_phone = _formval("captain_phone")
    if not team_name:
        errors["team_name"] = "Team name is required."
    if not captain_name:
        errors["captain_name"] = "Captain name is required."
    if not _is_valid_phone(captain_phone):
        errors["captain_phone"] = "Phone number must contain exactly 10 digits."

    players = {}
    for i in range(1, 5):
        name = _formval(f"player_{i}_name")
        uid = _formval(f"player_{i}_uid")
        level_raw = _formval(f"player_{i}_level")
        if not name:
            errors[f"player_{i}_name"] = f"Player {i} name is required."
        if not _is_valid_uid(uid):
            errors[f"player_{i}_uid"] = INVALID_UID_MSG.format(idx=i)
        if not _is_valid_level(level_raw):
            try:
                val = int(level_raw)
            except (TypeError, ValueError):
                val = level_raw if level_raw else 0
            errors[f"player_{i}_level"] = INVALID_LEVEL_MSG.format(idx=i, val=val)
        players[i] = {"name": name, "uid": uid, "level_raw": level_raw}

    transaction_id = _formval("payment_transaction_id")
    if not transaction_id:
        errors["payment_transaction_id"] = "Please enter your payment transaction ID."

    if "payment_screenshot" not in request.files:
        errors["payment_screenshot"] = "Please upload your payment screenshot."
    else:
        f = request.files["payment_screenshot"]
        if not f or not getattr(f, "filename", None):
            errors["payment_screenshot"] = "Please upload your payment screenshot."

    if tournament is None:
        errors["_general"] = "Tournament not found."
        return errors, players, team_name, captain_name, captain_phone, transaction_id

    if not tournament.status == "OPEN":
        errors["_general"] = "Registration for this tournament is closed."
    elif tournament.registration_deadline:
        deadline = tournament.registration_deadline
        if deadline.tzinfo is not None:
            deadline = deadline.replace(tzinfo=None)
        if datetime.utcnow() > deadline:
            errors["_general"] = "Registration for this tournament is closed."

    if team_name and tournament:
        duplicate = (
            Registration.query.filter_by(
                tournament_id=tournament.id, team_name=team_name
            ).first()
        )
        if duplicate:
            errors["team_name"] = "Team name is already registered for this tournament."

    if tournament and tournament.confirmed_count >= tournament.max_teams:
        errors["_general"] = "This tournament is full."

    return errors, players, team_name, captain_name, captain_phone, transaction_id


def _flash_errors(errors):
    for field, msg in errors.items():
        if field == "_general":
            flash(msg, "danger")
        else:
            flash(f"{field}: {msg}", "danger")


@bp.route("/tournaments/<int:tournament_id>/register/submit", methods=["POST"])
def submit(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        abort(404)
    if not tournament.is_open_for_registration:
        flash("Registration for this tournament is closed.", "danger")
        return redirect(url_for("public.tournament_detail", tournament_id=tournament_id))

    (
        errors,
        players,
        team_name,
        captain_name,
        captain_phone,
        transaction_id,
    ) = _validate_registration(tournament)

    screenshot_filename = None
    if "payment_screenshot" in request.files and not errors.get(
        "payment_screenshot"
    ):
        file = request.files["payment_screenshot"]
        filename, save_errors = save_payment_screenshot(file, current_app.config)
        if save_errors:
            errors["payment_screenshot"] = save_errors[0]
        else:
            screenshot_filename = filename

    if errors:
        _flash_errors(errors)
        return redirect(url_for("public.register_start", tournament_id=tournament_id))

    registration = Registration(
        tournament_id=tournament.id,
        team_name=team_name,
        captain_name=captain_name,
        captain_phone=captain_phone,
        payment_transaction_id=transaction_id,
        payment_screenshot=screenshot_filename,
        payment_status="PAID_PENDING",
        registration_status="PENDING_PAYMENT_VERIFICATION",
    )
    db.session.add(registration)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        flash("Team name is already registered for this tournament.", "danger")
        return redirect(url_for("public.register_start", tournament_id=tournament_id))

    for idx in sorted(players.keys()):
        p = players[idx]
        db.session.add(
            Player(
                registration_id=registration.id,
                player_index=idx,
                name=p["name"],
                ff_uid=p["uid"],
                ff_level=int(p["level_raw"]),
            )
        )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Team name is already registered for this tournament.", "danger")
        return redirect(url_for("public.register_start", tournament_id=tournament_id))

    flash(
        "Registration submitted! Status: PENDING PAYMENT VERIFICATION. Save the details below to check your status later.",
        "success",
    )
    return render_template(
        "public/status_result.html",
        registration=registration,
        not_found=False,
        after_submit=True,
    )


@bp.route("/api/registrations", methods=["POST"])
def create():
    tournament_id_raw = _formval("tournament_id")
    try:
        tournament_id = int(tournament_id_raw)
    except (TypeError, ValueError):
        return {"ok": False, "errors": {"_general": "Invalid tournament."}}, 400
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        return {"ok": False, "errors": {"_general": "Tournament not found."}}, 404
    if not tournament.is_open_for_registration:
        return {"ok": False, "errors": {"_general": "Registration for this tournament is closed."}}, 400

    (
        errors,
        players,
        team_name,
        captain_name,
        captain_phone,
        transaction_id,
    ) = _validate_registration(tournament)

    screenshot_filename = None
    if "payment_screenshot" in request.files and not errors.get(
        "payment_screenshot"
    ):
        file = request.files["payment_screenshot"]
        filename, save_errors = save_payment_screenshot(file, current_app.config)
        if save_errors:
            errors["payment_screenshot"] = save_errors[0]
        else:
            screenshot_filename = filename

    if errors:
        return {"ok": False, "errors": errors}, 400

    registration = Registration(
        tournament_id=tournament.id,
        team_name=team_name,
        captain_name=captain_name,
        captain_phone=captain_phone,
        payment_transaction_id=transaction_id,
        payment_screenshot=screenshot_filename,
        payment_status="PAID_PENDING",
        registration_status="PENDING_PAYMENT_VERIFICATION",
    )
    db.session.add(registration)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return {
            "ok": False,
            "errors": {"team_name": "Team name is already registered for this tournament."},
        }, 400

    for idx in sorted(players.keys()):
        p = players[idx]
        db.session.add(
            Player(
                registration_id=registration.id,
                player_index=idx,
                name=p["name"],
                ff_uid=p["uid"],
                ff_level=int(p["level_raw"]),
            )
        )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {
            "ok": False,
            "errors": {"team_name": "Team name is already registered for this tournament."},
        }, 400

    return {
        "ok": True,
        "registration_id_internal": registration.id,
        "registration_status": registration.registration_status,
        "next": url_for(
            "public.status_lookup"
        ),
    }, 201
