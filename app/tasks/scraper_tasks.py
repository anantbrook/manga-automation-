import os
import asyncio
import aiohttp
from app.core.celery_app import celery_app
from app.models import db
from app.models.manga import Manga
from app.models.chapter import Chapter
from app.core.logger import logger
from app.scraper.factory import ScraperFactory
from datetime import datetime

async def async_download_chapter(chapter_id, source, chapter_url):
    scraper = ScraperFactory.get_scraper_by_source(source)
    if not scraper:
        logger.error(f"No scraper supports source: {source}")
        return False

    images = await scraper.get_chapter_images(chapter_url)
    if not images:
        logger.error(f"Failed to fetch images for chapter {chapter_id} from {chapter_url}")
        return False

    parts = chapter_id.split('/')
    if len(parts) < 2:
        return False
    manga_id = parts[0]
    slug = parts[-1]

    save_dir = os.path.join('static', 'manga', manga_id, slug)
    os.makedirs(save_dir, exist_ok=True)

    success_count = 0
    for idx, img_url in enumerate(images):
        ext = img_url.split('.')[-1].split('?')[0]
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
        filename = f"{idx:03d}.{ext}"
        filepath = os.path.join(save_dir, filename)

        referer = None
        if source == "manganato":
            referer = "https://manganato.com/"
        elif source == "asurascans":
            referer = "https://asuracomic.net/"

        success = await scraper.download_image(img_url, filepath, referer=referer)
        if success:
            success_count += 1
        else:
            logger.warning(f"Failed to download image {img_url}")

    if success_count > 0:
        # We need to defer importing create_app to avoid circular dependencies when running celery
        from app import create_app
        app = create_app()
        with app.app_context():
            chapter = db.session.get(Chapter, chapter_id)
            if chapter:
                chapter.is_downloaded = True
                chapter.local_path = save_dir
                db.session.commit()
                logger.info(f"Successfully downloaded and cached chapter {chapter_id}")

                # Integration with auto-sharing bot feature
                try:
                    from telegram import Bot
                    import os
                    token = os.getenv('TELEGRAM_BOT_TOKEN')
                    if token:
                        bot_instance = Bot(token=token)
                        from bot import broadcast_new_chapter

                        # Run the broadcast in the event loop safely
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        loop.run_until_complete(broadcast_new_chapter(bot_instance, chapter.manga.title, chapter.manga.id, chapter.title, slug))
                except Exception as e:
                    logger.error(f"Failed to broadcast chapter to Telegram: {e}")

        return True
    return False

@celery_app.task(bind=True, max_retries=3)
def download_chapter_images(self, chapter_id, source, chapter_url):
    logger.info(f"Downloading images for chapter {chapter_id}")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(async_download_chapter(chapter_id, source, chapter_url))
    if not result:
        raise self.retry(countdown=60)
    return result

async def async_fetch_and_add_manga(url):
    scraper = ScraperFactory.get_scraper_by_url(url)
    if not scraper:
        logger.error(f"No scraper supports URL: {url}")
        return {"status": "error", "message": "Unsupported URL"}

    details = await scraper.parse_url_to_manga(url)
    if not details:
        logger.error(f"Failed to fetch details for URL: {url}")
        return {"status": "error", "message": "Failed to fetch details"}

    manga_id = details['id']
    from app import create_app
    app = create_app()
    with app.app_context():
        manga = db.session.get(Manga, manga_id)
        if not manga:
            manga = Manga(
                id=manga_id,
                title=details['title'],
                cover_url=details['cover_url'],
                synopsis=details['synopsis'],
                source=details['source']
            )
            db.session.add(manga)
        else:
            manga.title = details['title']
            manga.cover_url = details['cover_url']
            manga.synopsis = details['synopsis']
            manga.last_updated = datetime.utcnow()

        for chap in details['chapters']:
            chapter = db.session.get(Chapter, chap['id'])
            if not chapter:
                chapter = Chapter(
                    id=chap['id'],
                    manga_id=manga_id,
                    title=chap['title'],
                    url=chap['url'],
                    number=chap['number']
                )
                db.session.add(chapter)

        db.session.commit()
        logger.info(f"Manga {manga_id} and its chapters added to DB.")

        chapters_to_dl = Chapter.query.filter_by(manga_id=manga_id, is_downloaded=False).all()
        for c in chapters_to_dl:
            download_chapter_images.delay(c.id, details['source'], c.url)

    return {"status": "success", "manga_id": manga_id}

@celery_app.task(bind=True, max_retries=3)
def fetch_and_add_manga_from_url(self, url):
    logger.info(f"Starting task: fetch_and_add_manga_from_url for {url}")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(async_fetch_and_add_manga(url))
    return result

@celery_app.task(bind=True)
def auto_downloader_cron(self):
    logger.info("Starting auto_downloader_cron job")
    from app import create_app
    app = create_app()
    with app.app_context():
        mangas = Manga.query.all()
        for manga in mangas:
            logger.info(f"Checking updates for {manga.title} ({manga.id}) from {manga.source}")
            url = None
            if manga.source == "aquareader":
                url = f"https://aquareader.net/manga/{manga.id}"
            elif manga.source == "mangadex":
                url = f"https://mangadex.org/title/{manga.id}/manga"

            if url:
                fetch_and_add_manga_from_url.delay(url)
