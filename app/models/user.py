from app.models.db import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Campos relacionados à assinatura
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    subscription_status = db.Column(db.String(50), default='inactive')
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Relacionamento com os PDFs
    pdfs = db.relationship('PDF', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_subscribed(self):
        return self.subscription_status == 'active' and \
               (self.subscription_end_date is None or \
                self.subscription_end_date > datetime.utcnow()) 