from datetime import datetime
from extensions import db

class CheckIn(db.Model):
    __tablename__ = 'checkins'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    energy = db.Column(db.Integer, nullable=False)
    sleep = db.Column(db.Integer, nullable=False)
    mood = db.Column(db.Integer, nullable=False)
    pain = db.Column(db.Integer, nullable=False)
    appetite = db.Column(db.Integer, nullable=False)
    stress = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    risk_score = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), nullable=True)
    warning_message = db.Column(db.Text, nullable=True)