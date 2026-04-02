from flask import Blueprint, jsonify, send_file
import os
import zipfile
import io
from app.models import db
from app.models.chapter import Chapter

chapter_bp = Blueprint('chapter', __name__)

@chapter_bp.route('/<path:manga_id>/<chapter_slug>', methods=['GET'])
def get_chapter(manga_id, chapter_slug):
    chapter_id = f"{manga_id}/{chapter_slug}"
    chapter = db.session.get(Chapter, chapter_id)

    if not chapter:
        return jsonify({"error": "Chapter not found in DB"}), 404

    if not chapter.is_downloaded or not chapter.local_path:
        return jsonify({"error": "Chapter not yet downloaded locally. Task is likely pending.", "status": "pending"}), 202

    if not os.path.exists(chapter.local_path):
        return jsonify({"error": "Local files not found on disk"}), 500

    files = sorted(os.listdir(chapter.local_path))
    images = []

    for f in files:
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            # Using absolute path from the root url to the static folder for serving
            images.append(f"/{chapter.local_path}/{f}")

    return jsonify({"images": images, "is_downloaded": True})

@chapter_bp.route('/download/<path:manga_id>/<chapter_slug>', methods=['GET'])
def download_chapter_zip(manga_id, chapter_slug):
    chapter_id = f"{manga_id}/{chapter_slug}"
    chapter = db.session.get(Chapter, chapter_id)

    if not chapter or not chapter.is_downloaded or not chapter.local_path:
        return jsonify({"error": "Chapter not available for download yet."}), 404

    if not os.path.exists(chapter.local_path):
        return jsonify({"error": "Local files missing"}), 500

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(chapter.local_path)):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                file_path = os.path.join(chapter.local_path, f)
                zf.write(file_path, arcname=f)

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name=f"{manga_id}-{chapter_slug}.zip",
        as_attachment=True,
        mimetype='application/zip'
    )
