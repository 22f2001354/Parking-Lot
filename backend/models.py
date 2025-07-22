from .database import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    pwd = db.Column(db.String, nullable=False)
    fullname = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    pincode = db.Column(db.String, nullable=False)
    role = db.Column(db.String, default="user")  

    reservations = db.relationship("Reservation", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.fullname} - {self.email}>"


class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.String, nullable=False)
    pincode = db.Column(db.String, nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)

    spots = db.relationship(
        "ParkingSpot",
        backref="lot",
        cascade="all, delete-orphan",
        lazy='dynamic'
    )

    @property
    def occupied_count(self):
        return self.spots.filter_by(status='O').count()

    def __repr__(self):
        return f"<ParkingLot {self.name} - {self.address}>"


class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey("parking_lot.id"), nullable=False)
    status = db.Column(db.String(1), default="A")  

    reservations = db.relationship(
        "Reservation",
        backref="spot",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):
        return f"<ParkingSpot ID {self.id} - Lot {self.lot_id} - Status {self.status}>"


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey("parking_spot.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    vehicle_no = db.Column(db.String, nullable=True)
    parked_at = db.Column(db.DateTime, default=datetime.utcnow)
    released_at = db.Column(db.DateTime, nullable=True)

    def calculate_cost(self):
        """Calculate cost based on time parked"""
        if self.released_at and self.parked_at:
            duration_hours = (self.released_at - self.parked_at).total_seconds() / 3600
            return round(duration_hours * self.spot.lot.price_per_hour, 2)
        return None

    def __repr__(self):
        return f"<Reservation {self.id} | Spot {self.spot_id} | User {self.user_id}>"
