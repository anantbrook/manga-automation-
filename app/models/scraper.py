from app.models import db
from datetime import datetime

class ScraperHealth(db.Model):
    __tablename__ = 'scraper_health'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False) # 'success' or 'failed'
    response_time = db.Column(db.Float, nullable=True) # in seconds
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
