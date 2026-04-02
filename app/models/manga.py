from datetime import datetime
from app.models import db

class Manga(db.Model):
    __tablename__ = 'manga'
    id = db.Column(db.String(255), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    cover_url = db.Column(db.String(512))
    synopsis = db.Column(db.Text)
    source = db.Column(db.String(100), default='aquareader') # To track origin
    views = db.Column(db.Integer, default=0) # For Trending/Popular sorting
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    chapters = db.relationship('Chapter', backref='manga', lazy=True, cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='manga', lazy=True, cascade='all, delete-orphan')
