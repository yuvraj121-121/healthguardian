from datetime import datetime
from extensions import db

class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    total_values = db.Column(db.Integer, default=0)
    normal_values = db.Column(db.Integer, default=0)
    abnormal_values = db.Column(db.Integer, default=0)
    critical_values = db.Column(db.Integer, default=0)
    overall_status = db.Column(db.String(50), nullable=True)
    recommendation = db.Column(db.Text, nullable=True)
    urgent = db.Column(db.Boolean, default=False)
    raw_results = db.Column(db.Text, nullable=True)
    ai_analysis = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Report {self.original_name}>'