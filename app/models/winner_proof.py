from datetime import datetime
from app import db


class WinnerProof(db.Model):
    __tablename__ = "winner_proofs"

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    image_path = db.Column(db.String(200), nullable=False)
    published = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tournament = db.relationship("Tournament", back_populates="winners", foreign_keys=[tournament_id])

    def __repr__(self):
        return f"<WinnerProof {self.id} {self.title}>"
