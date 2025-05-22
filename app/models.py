from flask_login import UserMixin
from app import db
from datetime import datetime
import json

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # 'customer', 'clerk', 'manager'
    is_travel_company = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_id)

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))

    user = db.relationship('User', backref='customer_profile')

class TravelCompany(db.Model):
    __tablename__ = 'travel_companies'
    company_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True)
    name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    billing_details = db.Column(db.Text)

    user = db.relationship('User', backref='travel_company_profile')

class RoomType(db.Model):
    __tablename__ = 'room_types'
    type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

    rooms = db.relationship('Room', backref='room_type', lazy=True)

class Room(db.Model):
    __tablename__ = 'rooms'
    room_id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('room_types.type_id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')
    price_per_night = db.Column(db.Float, nullable=False)
    weekly_rate = db.Column(db.Float, nullable=True)
    monthly_rate = db.Column(db.Float, nullable=True)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    reservation_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.room_id'), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    number_of_occupants = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('Customer', backref='reservations')
    room = db.relationship('Room', backref='reservations')

class TravelCompanyBooking(db.Model):
    __tablename__ = 'travel_company_bookings'
    booking_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('travel_companies.company_id'), nullable=False)
    reservation_ids = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    discount_rate = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('TravelCompany', backref='bookings')

class Billing(db.Model):
    __tablename__ = 'billings'
    billing_id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.reservation_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservation = db.relationship('Reservation', backref='billing')

class PaymentStatus:
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'