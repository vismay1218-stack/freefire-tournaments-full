from datetime import datetime
from decimal import Decimal, InvalidOperation
from flask import render_template, request, redirect, url_for, flash, abort
from app.routes.admin_tournaments import bp
from app.auth.admin import login_required_admin
from app import db
from app.models.tournament import Tournament, TOURNAMENT_STATUSES


def parse_decimal(value, field_name, errors):
    if value is None or value == "":
        errors[field_name] = "This field is required."
        return None
    try:
        d = Decimal(str(value))
        if d < 0:
            errors[field_name] = "Must be >= 0."
            return None
        return d
    except (InvalidOperation, ValueError):
        errors[field_name] = "Must be a valid number."
        return None


def parse_int(value, field_name, errors, min_val=1):
    if value is None or value == "":
        errors[field_name] = "This field is required."
        return None
    try:
        i = int(str(value))
        if i < min_val:
            errors[field_name] = f"Must be >= {min_val}."
            return None
        return i
    except (ValueError, TypeError):
        errors[field_name] = "Must be a valid integer."
        return None


def parse_datetime_local(value, field_name, errors):
    if not value:
        errors[field_name] = "This field is required."
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        errors[field_name] = "Invalid date/time format."
        return None


def validate_tournament_form(form):
    errors = {}
    data = {}

    name = (form.get("name") or "").strip()
    if not name:
        errors["name"] = "Name is required."
    else:
        data["name"] = name

    data["description"] = (form.get("description") or "").strip() or ""

    data["entry_fee"] = parse_decimal(form.get("entry_fee"), "entry_fee", errors)
    data["prize_pool"] = parse_decimal(form.get("prize_pool"), "prize_pool", errors)

    date_val = (form.get("date") or "").strip()
    if not date_val:
        errors["date"] = "Date is required."
    else:
        data["date"] = date_val

    time_val = (form.get("time") or "").strip()
    if not time_val:
        errors["time"] = "Time is required."
    else:
        data["time"] = time_val

    map_name = (form.get("map_name") or "").strip()
    if not map_name:
        errors["map_name"] = "Map name is required."
    else:
        data["map_name"] = map_name

    data["max_teams"] = parse_int(form.get("max_teams"), "max_teams", errors, min_val=1)

    data["registration_deadline"] = parse_datetime_local(
        form.get("registration_deadline"), "registration_deadline", errors
    )

    data["rules"] = (form.get("rules") or "").strip() or ""

    status = (form.get("status") or "").strip()
    if status not in TOURNAMENT_STATUSES:
        errors["status"] = "Invalid status."
    else:
        data["status"] = status

    return data, errors


@bp.route("/admin/tournaments")
@login_required_admin
def list_():
    tournaments = (
        Tournament.query.order_by(Tournament.created_at.desc()).all()
    )
    return render_template("admin/tournaments/list.html", tournaments=tournaments)


@bp.route("/admin/tournaments/new", methods=["GET", "POST"])
@login_required_admin
def create():
    if request.method == "POST":
        data, errors = validate_tournament_form(request.form)
        if errors:
            flash("Please correct the errors below.", "danger")
            return render_template(
                "admin/tournaments/form.html",
                tournament=None,
                form_data=request.form,
                errors=errors,
            ), 400

        tournament = Tournament(
            name=data["name"],
            description=data["description"],
            entry_fee=data["entry_fee"],
            prize_pool=data["prize_pool"],
            date=data["date"],
            time=data["time"],
            map_name=data["map_name"],
            max_teams=data["max_teams"],
            registration_deadline=data["registration_deadline"],
            rules=data["rules"],
            status=data["status"],
        )
        db.session.add(tournament)
        db.session.commit()
        flash(f"Tournament '{tournament.name}' created successfully.", "success")
        return redirect(url_for("admin_tournaments.list_"))

    return render_template(
        "admin/tournaments/form.html",
        tournament=None,
        form_data=None,
        errors=None,
    )


@bp.route("/admin/tournaments/<int:tournament_id>")
@login_required_admin
def view(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)
    registrations = sorted(
        tournament.registrations, key=lambda r: r.created_at, reverse=True
    )
    return render_template(
        "admin/tournaments/view.html",
        tournament=tournament,
        registrations=registrations,
    )


@bp.route("/admin/tournaments/<int:tournament_id>/edit", methods=["GET", "POST"])
@login_required_admin
def edit(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)

    if request.method == "POST":
        data, errors = validate_tournament_form(request.form)
        if errors:
            flash("Please correct the errors below.", "danger")
            return render_template(
                "admin/tournaments/form.html",
                tournament=tournament,
                form_data=request.form,
                errors=errors,
            ), 400

        tournament.name = data["name"]
        tournament.description = data["description"]
        tournament.entry_fee = data["entry_fee"]
        tournament.prize_pool = data["prize_pool"]
        tournament.date = data["date"]
        tournament.time = data["time"]
        tournament.map_name = data["map_name"]
        tournament.max_teams = data["max_teams"]
        tournament.registration_deadline = data["registration_deadline"]
        tournament.rules = data["rules"]
        tournament.status = data["status"]
        db.session.commit()
        flash(f"Tournament '{tournament.name}' updated successfully.", "success")
        return redirect(url_for("admin_tournaments.view", tournament_id=tournament.id))

    return render_template(
        "admin/tournaments/form.html",
        tournament=tournament,
        form_data=None,
        errors=None,
    )


@bp.route("/admin/tournaments/<int:tournament_id>/delete", methods=["POST"])
@login_required_admin
def delete(tournament_id):
    tournament = db.get_or_404(Tournament, tournament_id)
    name = tournament.name
    db.session.delete(tournament)
    db.session.commit()
    flash(f"Tournament '{name}' deleted.", "info")
    return redirect(url_for("admin_tournaments.list_"))
