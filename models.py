from app import db
from datetime import datetime

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
