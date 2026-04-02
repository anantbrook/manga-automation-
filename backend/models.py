from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Manga(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    source = db.Column(db.String(50), nullable=False, default='aquareader')
    title = db.Column(db.String(255), nullable=False)
    cover_url = db.Column(db.String(512))
    synopsis = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Allow composite ID+source if needed, but for now ID is usually unique per source

class Chapter(db.Model):
    id = db.Column(db.String(255), primary_key=True) # Format: manga_id/chapter_slug
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    # Order for sorting natively
    number = db.Column(db.Float, default=0)

class Subscription(db.Model):
    __table_args__ = (
        db.UniqueConstraint('chat_id', 'manga_id', name='uq_sub'),
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.String(255), nullable=False)
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id'), nullable=False)
