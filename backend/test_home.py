import asyncio
from app import create_app
from models import db, Manga

app = create_app()
with app.app_context():
    print(Manga.query.count())
    print("Done")
