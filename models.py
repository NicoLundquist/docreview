from app import db
from datetime import datetime
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint

# User authentication models (required for Replit Auth)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship to compliance reviews
    compliance_reviews = db.relationship('ComplianceReview', backref='user', lazy=True)

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class ComplianceReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_spec_filename = db.Column(db.String(255), nullable=False)
    submittal_filename = db.Column(db.String(255), nullable=False)
    overall_status = db.Column(db.String(50), nullable=True)
    models_reviewed = db.Column(db.Integer, nullable=True)
    compliant_models = db.Column(db.Integer, nullable=True)
    report_content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, completed, error
    error_message = db.Column(db.Text, nullable=True)
    
    # Link to the user who created the review
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
