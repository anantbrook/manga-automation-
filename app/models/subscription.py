from app.models import db

class Subscription(db.Model):
    __tablename__ = 'subscription'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.String(255), nullable=False)
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id', ondelete='CASCADE'), nullable=False)
