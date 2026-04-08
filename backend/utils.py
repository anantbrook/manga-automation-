import os
from werkzeug.utils import secure_filename

def get_safe_manga_dir(base_path, source, manga_id, chapter_slug):
    """
    Constructs a safe directory path for manga images, preventing path traversal.
    Returns None if any component is invalid or attempts traversal.
    """
    def is_safe(component):
        # Additional check to ensure secure_filename didn't just return something
        # that could be interpreted as a traversal or is empty.
        if not component:
            return False
        # Werkzeug's secure_filename should handle this, but we're being extra cautious.
        if component in (os.curdir, os.pardir):
            return False
        return True

    safe_source = secure_filename(source)
    if not is_safe(safe_source):
        return None

    id_parts = []
    for part in manga_id.split('/'):
        # Skip empty parts from split
        if not part:
            continue
        safe_part = secure_filename(part)
        if is_safe(safe_part):
            id_parts.append(safe_part)

    if not id_parts:
        return None

    safe_chapter_slug = secure_filename(chapter_slug)
    if not is_safe(safe_chapter_slug):
        return None

    # Construct final path
    try:
        final_path = os.path.join(base_path, safe_source, *id_parts, safe_chapter_slug)
    except TypeError:
        # Should not happen with our checks, but for safety
        return None

    # Final safety check: ensure the normalized path starts with base_path
    base_path_norm = os.path.normpath(base_path)
    final_path_norm = os.path.normpath(final_path)

    if not final_path_norm.startswith(base_path_norm):
        return None

    return final_path
