from flask import render_template, redirect, url_for, flash, request, current_app, abort
from app.routes.admin_winners import bp
from app.auth.admin import login_required_admin
from app import db
from app.models.winner_proof import WinnerProof
from app.models.tournament import Tournament
from app.services import upload_service


@bp.route("/admin/winners")
@login_required_admin
def list_():
    winners = db.session.execute(
        db.select(WinnerProof).order_by(WinnerProof.created_at.desc())
    ).scalars().all()
    return render_template("admin/winners/list.html", winners=winners)


@bp.route("/admin/winners/new", methods=["GET", "POST"])
@login_required_admin
def create():
    tournaments = db.session.execute(
        db.select(Tournament).order_by(Tournament.created_at.desc())
    ).scalars().all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        tournament_id_raw = request.form.get("tournament_id", "").strip()
        published = request.form.get("published") == "on"
        file = request.files.get("image")

        errors = []
        if not title:
            errors.append("Title is required.")
        if not file or not file.filename:
            errors.append("Image file is required.")

        tournament_id = None
        if tournament_id_raw:
            try:
                tournament_id = int(tournament_id_raw)
            except ValueError:
                errors.append("Invalid tournament selection.")

        image_uuid = None
        if file and file.filename and not errors:
            image_uuid, save_errors = upload_service.save_winner_image(file, current_app.config)
            errors.extend(save_errors)

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "admin/winners/form.html",
                winner=None,
                tournaments=tournaments,
            )

        winner = WinnerProof(
            tournament_id=tournament_id,
            title=title,
            description=description,
            image_path=image_uuid,
            published=published,
        )
        db.session.add(winner)
        db.session.commit()
        flash("Winner/proof added successfully.", "success")
        return redirect(url_for("admin_winners.list_"))

    return render_template("admin/winners/form.html", winner=None, tournaments=tournaments)


@bp.route("/admin/winners/<int:winner_id>/edit", methods=["GET", "POST"])
@login_required_admin
def edit(winner_id):
    winner = db.session.get(WinnerProof, winner_id)
    if not winner:
        abort(404)

    tournaments = db.session.execute(
        db.select(Tournament).order_by(Tournament.created_at.desc())
    ).scalars().all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        tournament_id_raw = request.form.get("tournament_id", "").strip()
        published = request.form.get("published") == "on"
        file = request.files.get("image")

        errors = []
        if not title:
            errors.append("Title is required.")

        tournament_id = None
        if tournament_id_raw:
            try:
                tournament_id = int(tournament_id_raw)
            except ValueError:
                errors.append("Invalid tournament selection.")

        old_image_path = winner.image_path
        image_changed = False
        if file and file.filename:
            image_uuid, save_errors = upload_service.save_winner_image(file, current_app.config)
            errors.extend(save_errors)
            if not save_errors:
                winner.image_path = image_uuid
                image_changed = True

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "admin/winners/form.html",
                winner=winner,
                tournaments=tournaments,
            )

        winner.tournament_id = tournament_id
        winner.title = title
        winner.description = description
        winner.published = published
        db.session.commit()
        if image_changed:
            upload_service.delete_stored_image(
                old_image_path, current_app.config, purpose="winner"
            )
        flash("Winner/proof updated successfully.", "success")
        return redirect(url_for("admin_winners.list_"))

    return render_template("admin/winners/form.html", winner=winner, tournaments=tournaments)


@bp.route("/admin/winners/<int:winner_id>/delete", methods=["POST"])
@login_required_admin
def delete(winner_id):
    winner = db.session.get(WinnerProof, winner_id)
    if not winner:
        abort(404)

    image_path = winner.image_path
    db.session.delete(winner)
    db.session.commit()
    upload_service.delete_stored_image(
        image_path, current_app.config, purpose="winner"
    )

    flash("Winner/proof deleted.", "success")
    return redirect(url_for("admin_winners.list_"))


@bp.route("/admin/winners/<int:winner_id>/toggle-publish", methods=["POST"])
@login_required_admin
def toggle_publish(winner_id):
    winner = db.session.get(WinnerProof, winner_id)
    if not winner:
        abort(404)

    winner.published = not winner.published
    db.session.commit()

    status = "published" if winner.published else "unpublished"
    flash(f"Winner/proof {status}.", "success")
    return redirect(url_for("admin_winners.list_"))
