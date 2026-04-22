from app import create_app
from models import db, Manga
import datetime

app = create_app()
with app.app_context():
    # Insert some dummy manga to ensure we have "latest" updates
    for i in range(5):
        m = Manga(
            id=f"dummy-manga-{i}",
            title=f"New Release {i}",
            source="mangadex",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            cover_url=None
        )
        if not db.session.get(Manga, m.id):
            db.session.add(m)
    db.session.commit()
    print(f"Total mangas in DB: {Manga.query.count()}")
