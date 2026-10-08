from app import db


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False, index=True)
    player_index = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    ff_uid = db.Column(db.String(40), nullable=False)
    ff_level = db.Column(db.Integer, nullable=False)

    registration = db.relationship("Registration", back_populates="players", foreign_keys=[registration_id])

    __table_args__ = (
        db.UniqueConstraint("registration_id", "player_index", name="uq_player_reg_idx"),
        db.CheckConstraint(db.text("player_index between 1 and 4"), name="ck_player_idx"),
    )

    def __repr__(self):
        return f"<Player {self.id} idx={self.player_index} {self.name}>"
