from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)

class Mall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    location = db.Column(db.String(150))
    price = db.Column(db.Float, default=0)
    address = db.Column(db.Text)
    pincode = db.Column(db.String(10))
    total_slots = db.Column(db.Integer)
    spots = db.relationship('ParkingSpot', backref='lot', lazy=True)
    feedbacks = db.relationship('Feedback', backref='lot', lazy=True)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Available')
    vehicle_type = db.Column(db.String(20), default='4-wheeler')
    mall_id = db.Column(db.Integer, db.ForeignKey('mall.id'))
    reservations = db.relationship('Reservation', backref='spot', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    total_cost = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    duration_hours = db.Column(db.Integer, default=1)
    vehicle_type = db.Column(db.String(20))

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    lot_id = db.Column(db.Integer, db.ForeignKey('mall.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
