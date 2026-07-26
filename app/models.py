from datetime import datetime
from flask_login import UserMixin
from app import db

# USER DATABASE
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    dob = db.Column(db.Date)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    reservations = db.relationship("Reservation", backref="user", lazy=True)

# ADMIN 
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# PARKING LOT
class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.Text, nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    
    spots = db.relationship("ParkingSpot", backref="lot", lazy=True)

# parking spot
class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # 'A' or 'O'
    
    reservations = db.relationship("Reservation", backref="spot", lazy=True)

# reservation
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parking_time = db.Column(db.DateTime, nullable=False)
    leaving_time = db.Column(db.DateTime)
    cost_per_hour = db.Column(db.Float, nullable=False)
