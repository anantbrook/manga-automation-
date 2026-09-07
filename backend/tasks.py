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
        'schedule': 7200.0, # seconds (2 hours)
    }
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

    app = create_app()

    unique_manga_ids = []
    manga_sources = {}

    with app.app_context():
        subs = Subscription.query.all()
        unique_manga_ids = list(set([sub.manga_id for sub in subs]))
        for m_id in unique_manga_ids:
            m_obj = db.session.get(Manga, m_id)
            if m_obj:
                manga_sources[m_id] = m_obj.source

    async def _check_all_updates():
        for manga_id in unique_manga_ids:
            source = manga_sources.get(manga_id, 'mangadex')
            scraper = get_scraper(source)
            details = await scraper.get_manga_details(manga_id)
            await asyncio.sleep(2) # Non-blocking sleep

            if not details: continue

            with app.app_context():
                manga_obj = db.session.get(Manga, manga_id)
                if not manga_obj: continue

                new_chapters_added = False
                for chap in details['chapters']:
                    chap_id = chap['id']
                    existing = db.session.get(Chapter, chap_id)
                    if not existing:
                        chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=0)
                        db.session.add(chapter)
                        new_chapters_added = True

                if new_chapters_added:
                    db.session.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_check_all_updates())


@celery.task
def fetch_global_latest_updates_job():
    """
    Automatically crawls for new manga using get_latest_updates from scrapers
    to organically grow the database.
    """
    from app import create_app
    from models import db, Manga

    app = create_app()

    async def _fetch_updates():
        sources = ['mangadex', 'aquareader']
        for source in sources:
            scraper = get_scraper(source)
            try:
                updates = await scraper.get_latest_updates()
                if not updates:
                    continue

                with app.app_context():
                    added = 0
                    for item in updates:
                        manga_id = item.get('id')
                        existing = db.session.get(Manga, manga_id)
                        if not existing:
                            manga = Manga(
                                id=manga_id,
                                title=item.get('title'),
                                cover_url=item.get('cover_url'),
                                source=source
                            )
                            db.session.add(manga)
                            added += 1

                    if added > 0:
                        db.session.commit()
                        logger.info("Added %d new manga from %s", added, source)

            except Exception as e:
                logger.error("Failed to fetch latest updates for %s: %s", source, e)

            await asyncio.sleep(2)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_fetch_updates())

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
