from datetime import datetime, timedelta
from flask import render_template, request, abort, flash, redirect, url_for, current_app
from sqlalchemy import case
from app.routes.public import bp
from app import db
from app.models.tournament import Tournament
from app.models.registration import Registration
from app.models.winner_proof import WinnerProof


STATUS_ORDER = {"OPEN": 0, "DRAFT": 1, "CLOSED": 2, "COMPLETED": 3}


@bp.route("/")
def home():
    tourneys = (
        Tournament.query
        .order_by(
            case(
                (Tournament.status == "OPEN", 0),
                (Tournament.status == "DRAFT", 1),
                (Tournament.status == "CLOSED", 2),
                (Tournament.status == "COMPLETED", 3),
                else_=4
            ),
            Tournament.created_at.desc()
        )
        .limit(6)
        .all()
    )
    winners = (
        WinnerProof.query
        .filter(WinnerProof.published == True)
        .order_by(WinnerProof.created_at.desc())
        .limit(3)
        .all()
    )
    return render_template(
        "public/home.html",
        tournaments=tourneys,
        winners=winners,
        site_name=current_app.config.get("SITE_NAME", "Free Fire Tournaments"),
    )


@bp.route("/tournaments")
def tournaments():
    all_tournaments = (
        Tournament.query
        .order_by(
            case(
                (Tournament.status == "OPEN", 0),
                (Tournament.status == "DRAFT", 1),
                (Tournament.status == "CLOSED", 2),
                (Tournament.status == "COMPLETED", 3),
                else_=4
            ),
            Tournament.created_at.desc()
        )
        .all()
    )
    return render_template("public/tournaments.html", tournaments=all_tournaments)


@bp.route("/tournaments/<int:tournament_id>")
def tournament_detail(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if tournament is None:
        abort(404)
    return render_template("public/tournament_detail.html", tournament=tournament)


@bp.route("/tournaments/<int:tournament_id>/register")
def register_start(tournament_id):
    tournament = db.session.get(Tournament, tournament_id)
    if tournament is None:
        abort(404)
    if not tournament.is_open_for_registration:
        flash("Registration is not open for this tournament.", "warning")
        return redirect(url_for("public.tournament_detail", tournament_id=tournament.id))
    return render_template("public/register_step1.html", tournament=tournament)


@bp.route("/winners")
def winners():
    all_winners = (
        WinnerProof.query
        .filter(WinnerProof.published == True)
        .order_by(WinnerProof.created_at.desc())
        .all()
    )
    return render_template("public/winners.html", winners=all_winners)


@bp.route("/status", methods=["GET", "POST"])
def status_lookup():
    if request.method == "POST":
        reg_id_raw = request.form.get("registration_id", "")
        phone_raw = request.form.get("captain_phone", "")

        reg_id = reg_id_raw.strip()
        if reg_id:
            reg_id = reg_id.upper()

        phone = phone_raw.strip()
        phone_valid = len(phone) == 10 and phone.isdigit()

        registration = None
        if phone_valid and reg_id:
            registration = (
                Registration.query
                .filter(Registration.registration_id == reg_id)
                .filter(Registration.captain_phone == phone)
                .first()
            )
            if registration is None:
                pass

        if registration is None:
            return render_template("public/status_result.html", registration=None, not_found=True)
        return render_template("public/status_result.html", registration=registration, not_found=False)
    return render_template("public/status_lookup.html")


@bp.route("/api/tournaments")
def api_tournaments():
    tourneys = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return {
        "ok": True,
        "tournaments": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "entry_fee": str(t.entry_fee),
                "prize_pool": str(t.prize_pool),
                "date": t.date,
                "time": t.time,
                "map_name": t.map_name,
                "max_teams": t.max_teams,
                "confirmed_count": t.confirmed_count,
                "status": t.status,
                "is_open": t.is_open_for_registration,
                "registration_deadline": t.registration_deadline.isoformat() if t.registration_deadline else None,
            }
            for t in tourneys
        ],
    }


@bp.route("/api/tournaments/<int:tournament_id>")
def api_tournament_detail(tournament_id):
    t = db.session.get(Tournament, tournament_id)
    if not t:
        return {"ok": False, "error": "Tournament not found"}, 404
    return {
        "ok": True,
        "tournament": {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "entry_fee": str(t.entry_fee),
            "prize_pool": str(t.prize_pool),
            "date": t.date,
            "time": t.time,
            "map_name": t.map_name,
            "max_teams": t.max_teams,
            "confirmed_count": t.confirmed_count,
            "status": t.status,
            "rules": t.rules,
            "is_open": t.is_open_for_registration,
            "registration_deadline": t.registration_deadline.isoformat() if t.registration_deadline else None,
        },
    }


@bp.route("/api/winners")
def api_winners():
    winners_list = (
        WinnerProof.query
        .filter(WinnerProof.published == True)
        .order_by(WinnerProof.created_at.desc())
        .all()
    )
    return {
        "ok": True,
        "winners": [
            {
                "id": w.id,
                "title": w.title,
                "description": w.description,
                "image_url": url_for("public_media.winner_image", filename=w.image_path) if w.image_path else None,
                "tournament_name": w.tournament.name if w.tournament else None,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in winners_list
        ],
    }
