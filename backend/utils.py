import os
import redis
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.exception("Failed to initialize Redis client")
    redis_client = None

def invalidate_manga_cache(source, manga_id):
    if not redis_client:
        return
    try:
        redis_client.delete(f"manga:{source}:{manga_id}")
    except redis.RedisError:
        logger.exception(f"Failed to invalidate cache for manga:{source}:{manga_id}")

def get_safe_manga_dir(base_dir, source, manga_id, chapter_slug=None):
    """
    Securely constructs local file paths by sanitizing source, manga_id,
    and chapter_slug segments using secure_filename to block Path Traversal attempts.
    """
    safe_source = secure_filename(source)
    # Manga IDs can have hyphens and alphanumeric characters, secure_filename works well here
    safe_manga_id = secure_filename(manga_id)

    if not safe_source or not safe_manga_id:
        raise ValueError("Invalid source or manga_id")

    path = os.path.join(base_dir, safe_source, safe_manga_id)

    if chapter_slug:
        safe_chapter_slug = secure_filename(chapter_slug)
        if not safe_chapter_slug:
             raise ValueError("Invalid chapter_slug")
        path = os.path.join(path, safe_chapter_slug)

    return path
