from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)


class Auction(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text)

    starting_price = db.Column(db.Float)

    image = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    end_time = db.Column(
        db.DateTime,
        default=lambda: datetime.utcnow() + timedelta(hours=24)
    )

    user_id = db.Column(db.Integer)


class Bid(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    amount = db.Column(db.Float)

    auction_id = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship("User")