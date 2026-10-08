from datetime import datetime
from decimal import Decimal
from sqlalchemy import UniqueConstraint, select, func
from app import db


TOURNAMENT_STATUSES = ("DRAFT", "OPEN", "CLOSED", "COMPLETED")
REGISTRATION_STATUSES = ("PENDING_PAYMENT_VERIFICATION", "CONFIRMED", "REJECTED")
PAYMENT_STATUSES = ("UNPAID", "PAID_PENDING", "VERIFIED", "FAILED")


class Tournament(db.Model):
    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    entry_fee = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal(0))
    prize_pool = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal(0))
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    map_name = db.Column(db.String(80), default="Bermuda")
    max_teams = db.Column(db.Integer, nullable=False, default=48)
    registration_deadline = db.Column(db.DateTime, nullable=False)
    rules = db.Column(db.Text, default="")
    status = db.Column(db.String(20), nullable=False, default="DRAFT")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    registrations = db.relationship(
        "Registration", back_populates="tournament", cascade="all, delete-orphan",
        foreign_keys="Registration.tournament_id"
    )
    winners = db.relationship("WinnerProof", back_populates="tournament", foreign_keys="WinnerProof.tournament_id")

    __table_args__ = (
        db.CheckConstraint(status.in_(TOURNAMENT_STATUSES), name="ck_tournament_status"),
        db.CheckConstraint(max_teams >= 1, name="ck_max_teams_pos"),
    )

    @property
    def confirmed_count(self):
        from app.models.registration import Registration
        return (
            db.session.query(func.count(Registration.id))
            .filter(Registration.tournament_id == self.id)
            .filter(Registration.registration_status == "CONFIRMED")
            .scalar()
            or 0
        )

    @property
    def confirmed_teams_relation(self):
        return [r for r in self.registrations if r.registration_status == "CONFIRMED"]

    @property
    def is_open_for_registration(self):
        if self.status != "OPEN":
            return False
        deadline = self.registration_deadline
        if deadline:
            naive_deadline = deadline.replace(tzinfo=None) if deadline.tzinfo else deadline
            if datetime.utcnow() > naive_deadline:
                return False
        if self.confirmed_count >= self.max_teams:
            return False
        return True

    def __repr__(self):
        return f"<Tournament {self.id} {self.name}>"
