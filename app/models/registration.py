from datetime import datetime
from sqlalchemy import UniqueConstraint
from app import db


PAYMENT_STATUSES = ("UNPAID", "PAID_PENDING", "VERIFIED", "FAILED")
REGISTRATION_STATUSES = ("PENDING_PAYMENT_VERIFICATION", "CONFIRMED", "REJECTED")


class Registration(db.Model):
    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.String(40), unique=True, nullable=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True)
    team_name = db.Column(db.String(120), nullable=False)
    captain_name = db.Column(db.String(120), nullable=False)
    captain_phone = db.Column(db.String(20), nullable=False)
    payment_transaction_id = db.Column(db.String(200))
    payment_screenshot = db.Column(db.String(200))
    payment_status = db.Column(db.String(20), nullable=False, default="PAID_PENDING")
    registration_status = db.Column(db.String(40), nullable=False, default="PENDING_PAYMENT_VERIFICATION")
    rejection_reason = db.Column(db.Text)
    confirmation_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tournament = db.relationship("Tournament", back_populates="registrations", foreign_keys=[tournament_id])
    players = db.relationship(
        "Player", back_populates="registration", cascade="all, delete-orphan",
        foreign_keys="Player.registration_id", order_by="Player.player_index"
    )

    __table_args__ = (
        UniqueConstraint("tournament_id", "team_name", name="uq_team_per_tournament"),
        db.CheckConstraint(payment_status.in_(PAYMENT_STATUSES), name="ck_payment_status"),
        db.CheckConstraint(registration_status.in_(REGISTRATION_STATUSES), name="ck_reg_status"),
    )

    def __repr__(self):
        return f"<Registration {self.id} {self.team_name}>"
