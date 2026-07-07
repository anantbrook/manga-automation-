from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Manga(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    source = db.Column(db.String(50), nullable=False, default='aquareader')
    title = db.Column(db.String(255), nullable=False)
    cover_url = db.Column(db.String(512))
    synopsis = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    view_count = db.Column(db.Integer, default=0, index=True)

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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class ReadingHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id'), nullable=False)
    chapter_id = db.Column(db.String(255), nullable=False)
    last_read = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
