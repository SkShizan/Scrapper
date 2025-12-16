from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    otp = db.Column(db.String(6), nullable=True)
    otp_created_at = db.Column(db.DateTime, nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    is_approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    leads = db.relationship('Lead', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_otp(self):
        self.otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        self.otp_created_at = datetime.utcnow()
        return self.otp
    
    def verify_otp(self, otp):
        if not self.otp or not self.otp_created_at:
            return False
        from datetime import timedelta
        if datetime.utcnow() - self.otp_created_at > timedelta(minutes=10):
            return False
        if self.otp == otp:
            self.email_verified = True
            self.otp = None
            self.otp_created_at = None
            return True
        return False
    
    def can_access_app(self):
        if not (self.email_verified and self.is_approved and self.is_active):
            return False
        if self.is_super_admin or self.is_admin:
            return True
        if self.subscription_expires_at and datetime.utcnow() > self.subscription_expires_at:
            return False
        return True
    
    def is_subscription_expired(self):
        if self.is_super_admin or self.is_admin:
            return False
        if not self.subscription_expires_at:
            return False
        return datetime.utcnow() > self.subscription_expires_at
    
    def days_remaining(self):
        if not self.subscription_expires_at:
            return None
        if self.is_super_admin or self.is_admin:
            return float('inf')
        remaining = (self.subscription_expires_at - datetime.utcnow()).days
        return max(0, remaining)
    
    def extend_subscription(self, days):
        from datetime import timedelta
        if self.subscription_expires_at and self.subscription_expires_at > datetime.utcnow():
            self.subscription_expires_at = self.subscription_expires_at + timedelta(days=days)
        else:
            self.subscription_expires_at = datetime.utcnow() + timedelta(days=days)
    
    @property
    def status(self):
        if not self.email_verified:
            return 'pending_verification'
        if not self.is_approved:
            return 'pending_approval'
        if not self.is_active:
            return 'disabled'
        if self.is_subscription_expired():
            return 'expired'
        return 'active'


class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50))
    website = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(50), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'Name': self.name,
            'Email': self.email or 'N/A',
            'Phone': self.phone,
            'Website': self.website or 'N/A',
            'Location': self.location or 'N/A',
            'Source': self.source or 'N/A'
        }
