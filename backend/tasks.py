import os
from celery import Celery
import asyncio
import aiohttp
from scrapers import get_scraper

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery Beat to auto-scrape new chapters for Subscribed users every hour
celery.conf.beat_schedule = {
    'check-updates-every-hour': {
        'task': 'tasks.check_manga_updates_job',
        'schedule': 3600.0, # seconds (1 hour)
    },
}
celery.conf.timezone = 'UTC'

@celery.task
def check_manga_updates_job():
    """
    Background job managed by Celery Beat.
    Checks for updates on all subscribed manga.
    Since telegram bot is separate, it pushes updates via bot API or simply caches them
    so the bot can pick them up. (We'll trigger the scrape to refresh DB).
    """
    from app import create_app
    from models import db, Subscription, Manga, Chapter
    import time

    app = create_app()
    with app.app_context():
        subs = Subscription.query.all()
        unique_manga_ids = list(set([sub.manga_id for sub in subs]))

        scraper = get_scraper('mangadex')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for manga_id in unique_manga_ids:
            manga_obj = db.session.get(Manga, manga_id)
            if not manga_obj: continue

            # Re-scraping updates the DB directly (as written in the api_manga_details flow)
            details = loop.run_until_complete(scraper.get_manga_details(manga_id))
            time.sleep(2)

            if not details: continue

            for chap in details['chapters']:
                chap_id = chap['id']
                existing = db.session.get(Chapter, chap_id)
                if not existing:
                    chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=0)
                    db.session.add(chapter)

            db.session.commit()

@celery.task
def download_chapter_images_local(source: str, manga_id: str, chapter_slug: str):
    """
    Downloads all images for a given chapter to static/manga/<source>/<manga_id>/<chapter_slug>/
    """
    from app import create_app
    from utils import get_safe_manga_dir
    app = create_app()
    with app.app_context():
        scraper = get_scraper(source)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        images = loop.run_until_complete(scraper.get_chapter_images(manga_id, chapter_slug))

    if not images:
        return {'status': 'error', 'msg': 'No images found'}

    # Sanitize inputs and get safe local directory
    base_manga_path = os.path.join(os.path.dirname(__file__), 'static', 'manga')
    base_dir = get_safe_manga_dir(base_manga_path, source, manga_id, chapter_slug)

    if not base_dir:
        return {'status': 'error', 'msg': 'Invalid path components'}

    os.makedirs(base_dir, exist_ok=True)

    async def _download_all():
        async with aiohttp.ClientSession() as session:
            for idx, img_url in enumerate(images):
                try:
                    async with session.get(img_url) as resp:
                        resp.raise_for_status()
                        ext = img_url.split('.')[-1].split('?')[0]
                        if len(ext) > 4: ext = 'jpg'
                        filepath = os.path.join(base_dir, f"{idx:03d}.{ext}")

                        with open(filepath, 'wb') as f:
                            f.write(await resp.read())
                except Exception as e:
                    print(f"Failed to download {img_url}: {e}")

    loop.run_until_complete(_download_all())
    return {'status': 'success', 'path': base_dir, 'count': len(images)}
