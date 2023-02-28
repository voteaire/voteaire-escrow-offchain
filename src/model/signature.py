from . import db

from sqlalchemy import func


class Signature(db.Model):
    __tablename__ = "signature"

    id = db.Column(db.Integer, primary_key=True)

    proposal_id = db.Column(db.String, nullable=False)
    pubkey = db.Column(db.String, nullable=False)
    signature = db.Column(db.String, nullable=False)
    results = db.Column(db.String, nullable=False)

    script_input = db.Column(db.String, nullable=False)

    creation_date = db.Column(
        db.DateTime(timezone=False), server_default=func.now(), nullable=False
    )
