import os
from celery import Celery
import asyncio
import aiohttp
import logging
from scrapers import get_scraper
from utils import get_safe_manga_dir

logger = logging.getLogger(__name__)

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
    'fetch-global-latest-updates': {
        'task': 'tasks.fetch_global_latest_updates_job',
        'schedule': 7200.0, # seconds (2 hours)
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

        async def _check_all_updates():
            mangas = Manga.query.filter(Manga.id.in_(unique_manga_ids)).all()
            manga_dict = {m.id: m for m in mangas}

            for manga_id in unique_manga_ids:
                manga_obj = manga_dict.get(manga_id)
                if not manga_obj: continue

                # Re-scraping updates the DB directly
                details = await scraper.get_manga_details(manga_id)
                await asyncio.sleep(2) # Non-blocking sleep

                if not details: continue

                # Fetch all existing chapters for this manga at once
                chap_ids = [chap['id'] for chap in details['chapters']]
                existing_chapters = Chapter.query.filter(Chapter.id.in_(chap_ids)).all()
                existing_chapter_ids = {c.id for c in existing_chapters}

                for chap in details['chapters']:
                    chap_id = chap['id']
                    if chap_id not in existing_chapter_ids:
                        chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=0)
                        db.session.add(chapter)

                db.session.commit()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_check_all_updates())

@celery.task
def download_chapter_images_local(source: str, manga_id: str, chapter_slug: str):
    """
    Downloads all images for a given chapter to static/manga/<source>/<manga_id>/<chapter_slug>/
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        scraper = get_scraper(source)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        images = loop.run_until_complete(scraper.get_chapter_images(manga_id, chapter_slug))

    if not images:
        return {'status': 'error', 'msg': 'No images found'}

    base_manga_dir = os.path.join(os.path.dirname(__file__), 'static', 'manga')
    try:
        base_dir = get_safe_manga_dir(base_manga_dir, source, manga_id, chapter_slug)
    except ValueError:
        logger.error("Invalid path components for download: %s %s %s", source, manga_id, chapter_slug)
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
                    logger.exception("Failed to download %s", img_url)

    loop.run_until_complete(_download_all())
    return {'status': 'success', 'path': base_dir, 'count': len(images)}

@celery.task
def fetch_global_latest_updates_job():
    """
    Background job to crawl and populate the database with the latest manga updates.
    Runs periodically to organically grow the manga collection.
    """
    from app import create_app
    from models import db, Manga
    from scrapers import scrapers
    from datetime import datetime, timezone

    app = create_app()
    with app.app_context():
        async def _fetch_and_store():
            for source, scraper in scrapers.items():
                try:
                    latest = await scraper.get_latest_updates(limit=20)
                    for item in latest:
                        manga = db.session.get(Manga, item['id'])
                        if not manga:
                            manga = Manga(
                                id=item['id'],
                                title=item['title'],
                                source=item['source'],
                                cover_url=item['cover_url'],
                                last_updated=datetime.now(timezone.utc)
                            )
                            db.session.add(manga)
                        else:
                            manga.last_updated = datetime.now(timezone.utc)
                            if item.get('cover_url'):
                                manga.cover_url = item['cover_url']
                    db.session.commit()
                except Exception as e:
                    logger.exception("Error fetching latest updates for source %s: %s", source, e)
                    db.session.rollback()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_fetch_and_store())
