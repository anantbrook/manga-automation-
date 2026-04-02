import os
import requests
from flask import Blueprint, jsonify, request, send_from_directory, current_app, Response
from app.models import db
from app.models.manga import Manga
from app.models.chapter import Chapter

manga_bp = Blueprint('manga', __name__)

@manga_bp.route('/<path:manga_id>', methods=['GET'])
def get_manga(manga_id):
    manga = db.session.get(Manga, manga_id)
    if not manga:
        return jsonify({"error": "Manga not found"}), 404

    chapters = Chapter.query.filter_by(manga_id=manga.id).order_by(Chapter.number.desc()).all()

    # We will use the proxy endpoint for cover_url to avoid hotlinking
    cover = f"/api/manga/proxy-image?url={manga.cover_url}" if manga.cover_url else ""

    return jsonify({
        "id": manga.id,
        "title": manga.title,
        "cover_url": cover,
        "synopsis": manga.synopsis,
        "source": manga.source,
        "last_updated": manga.last_updated.isoformat() if manga.last_updated else None,
        "chapters": [{"id": c.id, "title": c.title, "number": c.number, "is_downloaded": c.is_downloaded} for c in chapters]
    })

@manga_bp.route('/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url:
        return "No url provided", 400

    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ''

    if (hostname == 'localhost' or
        hostname.startswith('127.') or
        hostname.startswith('10.') or
        hostname.startswith('192.168.') or
        hostname.startswith('172.') or
        hostname == '0.0.0.0' or
        hostname == '::1'):
        return "Invalid URL", 403

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        r.raise_for_status()

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in r.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(r.iter_content(chunk_size=10*1024),
                        status=r.status_code,
                        headers=headers,
                        content_type=r.headers.get('content-type', 'image/jpeg'))
    except Exception as e:
        return str(e), 500

@manga_bp.route('/', defaults={'path': ''})
@manga_bp.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(current_app.root_path, '../static/dist', path)):
        return send_from_directory(os.path.join(current_app.root_path, '../static/dist'), path)
    else:
        return send_from_directory(os.path.join(current_app.root_path, '../static/dist'), 'index.html')
