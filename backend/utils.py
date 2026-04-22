import os
from werkzeug.utils import secure_filename

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
