from flask import render_template
from sqlalchemy import func
from app.routes.admin_dashboard import bp
from app.auth.admin import login_required_admin
from app import db
from app.models.tournament import Tournament
from app.models.registration import Registration


@bp.route("/admin/dashboard")
@login_required_admin
def index():
    total_tournaments = db.session.query(func.count(Tournament.id)).scalar() or 0
    open_tournaments = (
        db.session.query(func.count(Tournament.id))
        .filter(Tournament.status == "OPEN")
        .scalar()
        or 0
    )

    total_registrations = db.session.query(func.count(Registration.id)).scalar() or 0
    confirmed_registrations = (
        db.session.query(func.count(Registration.id))
        .filter(Registration.registration_status == "CONFIRMED")
        .scalar()
        or 0
    )
    pending_registrations = (
        db.session.query(func.count(Registration.id))
        .filter(Registration.registration_status == "PENDING_PAYMENT_VERIFICATION")
        .scalar()
        or 0
    )
    rejected_registrations = (
        db.session.query(func.count(Registration.id))
        .filter(Registration.registration_status == "REJECTED")
        .scalar()
        or 0
    )

    recent_registrations = (
        Registration.query.options(
            db.joinedload(Registration.tournament)
        )
        .order_by(Registration.created_at.desc())
        .limit(10)
        .all()
    )

    pending_payments = (
        Registration.query.options(
            db.joinedload(Registration.tournament)
        )
        .filter(Registration.registration_status == "PENDING_PAYMENT_VERIFICATION")
        .order_by(Registration.created_at.asc())
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_tournaments=total_tournaments,
        open_tournaments=open_tournaments,
        total_registrations=total_registrations,
        confirmed_registrations=confirmed_registrations,
        pending_registrations=pending_registrations,
        rejected_registrations=rejected_registrations,
        recent_registrations=recent_registrations,
        pending_payments=pending_payments,
    )
