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
    'fetch-global-latest-updates-job': {
        'task': 'tasks.fetch_global_latest_updates_job',
        'schedule': 1800.0, # seconds (30 minutes)
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
            for manga_id in unique_manga_ids:
                manga_obj = db.session.get(Manga, manga_id)
                if not manga_obj: continue

                # Re-scraping updates the DB directly
                details = await scraper.get_manga_details(manga_id)
                await asyncio.sleep(2) # Non-blocking sleep

                if not details: continue

                existing_chapters = Chapter.query.filter_by(manga_id=manga_id).all()
                existing_chap_ids = {c.id for c in existing_chapters}

                new_chapters = []
                for chap in details['chapters']:
                    chap_id = chap['id']
                    if chap_id not in existing_chap_ids:
                        new_chapters.append(Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=0))
                        existing_chap_ids.add(chap_id)

                if new_chapters:
                    db.session.add_all(new_chapters)

                db.session.commit()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_check_all_updates())

@celery.task
def fetch_global_latest_updates_job():
    """
    Background job managed by Celery Beat.
    Crawls for new manga using get_latest_updates on scrapers (MangaDex, AquaReader) to organically grow the database.
    """
    from app import create_app
    from models import db, Manga
    from scrapers import scrapers

    app = create_app()
    with app.app_context():
        async def _fetch_global_updates():
            for source, scraper in scrapers.items():
                try:
                    results = await scraper.get_latest_updates()
                    for item in results:
                        existing = db.session.get(Manga, item['id'])
                        if not existing:
                            # We just add a skeleton, details will be fetched when user clicks
                            manga = Manga(id=item['id'], title=item['title'], source=source, cover_url=item.get('cover_url'))
                            db.session.add(manga)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Error fetching global updates for {source}: {e}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_fetch_global_updates())


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
