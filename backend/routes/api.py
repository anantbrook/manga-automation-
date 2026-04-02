import os
import asyncio
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request, send_file, Response, send_from_directory
from models import db, Manga, Chapter, Subscription
from scrapers import get_scraper
import urllib.parse
import socket
import ipaddress
import uuid
import zipfile
import io

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/search')
async def api_search():
    q = request.args.get('q', '')
    source = request.args.get('source', 'mangadex')
    if not q: return jsonify([])

    scraper = get_scraper(source)
    results = await scraper.search_manga(q)
    return jsonify(results)

@api_bp.route('/manga/<source>/<path:manga_id>')
async def api_manga_details(source, manga_id):
    manga = db.session.get(Manga, manga_id)
    force_update = request.args.get('force', 'false').lower() == 'true'

    cache_expired = False
    if manga and manga.last_updated:
        last_upd = manga.last_updated
        if last_upd.tzinfo is None:
            last_upd = last_upd.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_upd > timedelta(hours=6):
            cache_expired = True

    if manga and not force_update and manga.synopsis and not cache_expired:
        chapters = Chapter.query.filter_by(manga_id=manga_id).all()
        if chapters:
            return jsonify({
                'id': manga.id,
                'title': manga.title,
                'cover_url': manga.cover_url,
                'synopsis': manga.synopsis,
                'source': manga.source,
                'chapters': [{'id': c.id.split('/')[-1], 'title': c.title, 'url': c.url} for c in chapters]
            })

    scraper = get_scraper(source)
    details = await scraper.get_manga_details(manga_id)

    if not details:
        return jsonify({'error': 'Not found'}), 404

    if not manga:
        manga = Manga(id=details['id'], title=details['title'], source=source)
        db.session.add(manga)

    manga.cover_url = details['cover_url']
    manga.synopsis = details['synopsis']
    manga.last_updated = datetime.now(timezone.utc)

    for chap in details['chapters']:
        chap_id = chap['id']
        chapter = db.session.get(Chapter, chap_id)
        if not chapter:
            num = 0.0
            try:
                parts = chap['title'].lower().replace('chapter', '').strip().split()
                if parts: num = float(parts[0].replace('-', '.'))
            except (ValueError, IndexError, AttributeError): pass
            chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=num)
            db.session.add(chapter)

    db.session.commit()

    details['chapters'] = [{'id': c['id'].split('/')[-1], 'title': c['title'], 'url': c['url']} for c in details['chapters']]
    return jsonify(details)

@api_bp.route('/chapter/<source>/<path:manga_id>/<chapter_slug>')
async def api_chapter_images(source, manga_id, chapter_slug):
    # Check if we have it locally downloaded first
    local_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'manga', source, manga_id, chapter_slug)
    if os.path.exists(local_dir):
        files = sorted(os.listdir(local_dir))
        if files:
            # We have local files, serve them directly instead of scraping
            base_url = request.host_url.rstrip('/')
            images = [f"{base_url}/static/manga/{source}/{manga_id}/{chapter_slug}/{f}" for f in files]
            return jsonify({'images': images, 'local': True})

    # Otherwise fallback to scraping proxy urls
    scraper = get_scraper(source)
    images = await scraper.get_chapter_images(manga_id, chapter_slug)

    if not images:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'images': images, 'local': False})

@api_bp.route('/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url: return "No url provided", 400

    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ''

    try:
        ip = socket.gethostbyname(hostname)
        if ipaddress.ip_address(ip).is_private:
            return "Invalid URL: Private IP", 403
    except Exception:
        return "Invalid URL: Cannot resolve host", 400

    allowed_domains = ['aquareader.net', 'wp.com', 'mangadex.org', 'uploads.mangadex.org']
    if not any(domain in hostname for domain in allowed_domains):
        return "Domain not allowed", 403

    import requests
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://aquareader.net/" if 'aquareader' in url else "https://mangadex.org/"
    }

    try:
        r = requests.get(url, headers=headers, stream=True)
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

@api_bp.route('/download/<source>/<path:manga_id>/<chapter_slug>', methods=['POST'])
def api_download_chapter(source, manga_id, chapter_slug):
    from tasks import download_chapter_images_local

    # Trigger Celery Task
    task = download_chapter_images_local.delay(source, manga_id, chapter_slug)
    return jsonify({'job_id': task.id, 'status': 'queued'})

@api_bp.route('/download/status/<job_id>')
def api_download_status(job_id):
    from tasks import celery
    task = celery.AsyncResult(job_id)

    if task.state == 'PENDING':
        return jsonify({'status': 'pending'})
    elif task.state == 'SUCCESS':
        return jsonify({'status': 'completed', 'result': task.result})
    elif task.state == 'FAILURE':
        return jsonify({'status': 'error', 'error': str(task.info)})

    return jsonify({'status': task.state})

@api_bp.route('/download/zip/<source>/<path:manga_id>/<chapter_slug>')
def get_zip_download(source, manga_id, chapter_slug):
    local_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'manga', source, manga_id, chapter_slug)
    if not os.path.exists(local_dir):
        return jsonify({'error': 'Not downloaded locally yet'}), 404

    files = sorted(os.listdir(local_dir))
    if not files:
        return jsonify({'error': 'Directory empty'}), 404

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            filepath = os.path.join(local_dir, f)
            zf.write(filepath, f)

    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{manga_id}-{chapter_slug}.cbz", as_attachment=True, mimetype='application/zip')