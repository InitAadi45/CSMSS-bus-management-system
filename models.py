from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    User Model for authentication and roles: admin, staff, student.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'staff', 'student'
    phone = db.Column(db.String(15), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == 'admin'

    def is_staff(self):
        return self.role == 'staff'

    def is_student(self):
        return self.role == 'student'

class BusRoute(db.Model):
    """
    Bus Route Model containing route, timings, and live delay notifications.
    """
    id = db.Column(db.Integer, primary_key=True)
    route_name = db.Column(db.String(200), nullable=False)  # e.g., 'Chhatrapati Sambhajinagar - Paithan - Kanchanwadi'
    bus_number = db.Column(db.String(50), nullable=False)
    via_points = db.Column(db.String(500), nullable=False)  # e.g., 'CIDCO, Kranti Chowk, Railway Station'
    pickup_time = db.Column(db.String(50), nullable=False)  # e.g., '07:30 AM'
    dropoff_time = db.Column(db.String(50), nullable=False)  # e.g., '05:30 PM'
    status = db.Column(db.String(50), default="On Time")  # 'On Time', 'Delayed', 'Cancelled'
    delay_reason = db.Column(db.String(200), nullable=True)

class BusPass(db.Model):
    """
    Bus Pass Model tracking student payments, validity, and receipt files.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pass_type = db.Column(db.String(50), nullable=False)  # 'Monthly', 'Quarterly', 'Yearly'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default="Pending")  # 'Pending', 'Paid'
    payment_id = db.Column(db.String(100), nullable=True)
    receipt_url = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to user
    student = db.relationship('User', backref=db.backref('passes', lazy=True, cascade="all, delete-orphan"))

    @property
    def remaining_days(self):
        """
        Calculate remaining validity days of the pass.
        """
        today = date.today()
        if today > self.end_date:
            return 0
        elif today < self.start_date:
            return (self.end_date - self.start_date).days
        else:
            return (self.end_date - today).days

    @property
    def is_active(self):
        """
        Check if the pass is currently valid and paid.
        """
        today = date.today()
        return self.payment_status == 'Paid' and self.start_date <= today <= self.end_date

class Attendance(db.Model):
    """
    Student Daily Bus Attendance record.
    """
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey('bus_route.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # 'Present', 'Absent'
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('attendances', lazy=True, cascade="all, delete-orphan"))
    route = db.relationship('BusRoute', backref=db.backref('attendances', lazy=True))
    marker = db.relationship('User', foreign_keys=[marked_by])

class NewsNotice(db.Model):
    """
    General announcement and delay notifications.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bus_route_id = db.Column(db.Integer, db.ForeignKey('bus_route.id'), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    route = db.relationship('BusRoute', backref=db.backref('notices', lazy=True))
    author = db.relationship('User', foreign_keys=[author_id])
