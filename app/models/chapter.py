from app.models import db

class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.String(255), primary_key=True)
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    number = db.Column(db.Float, default=0)
    # Track if we have downloaded and cached this chapter locally
    is_downloaded = db.Column(db.Boolean, default=False)
    local_path = db.Column(db.String(512), nullable=True) # E.g., static/manga/solo-leveling/chapter-1/
