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
import logging
import requests
import json
import redis
from utils import get_safe_manga_dir

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
except Exception as e:
    logger.warning(f"Could not connect to Redis: {e}. Caching will be disabled.")
    redis_client = None

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/search')
async def api_search():
    q = request.args.get('q', '')
    source = request.args.get('source', 'mangadex')
    if not q: return jsonify([])

    cache_key = f"search:{source}:{q}"
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return Response(cached, mimetype='application/json')
        except redis.RedisError as e:
            logger.error(f"Redis error on get {cache_key}: {e}")

    scraper = get_scraper(source)
    results = await scraper.search_manga(q)

    if redis_client and results:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(results)) # Cache for 1 hour
        except redis.RedisError as e:
            logger.error(f"Redis error on set {cache_key}: {e}")

    return jsonify(results)

@api_bp.route('/home')
def api_home():
    # Trending based on views
    trending = Manga.query.order_by(Manga.view_count.desc()).limit(10).all()
    # Latest updated
    latest = Manga.query.order_by(Manga.last_updated.desc()).limit(10).all()

    def serialize(m):
        return {
            'id': m.id,
            'title': m.title,
            'cover_url': m.cover_url,
            'source': m.source,
            'views': m.view_count
        }

    return jsonify({
        'trending': [serialize(m) for m in trending],
        'latest': [serialize(m) for m in latest]
    })

@api_bp.route('/manga/<source>/<path:manga_id>')
async def api_manga_details(source, manga_id):
    force_update = request.args.get('force', 'false').lower() == 'true'
    cache_key = f"manga:{source}:{manga_id}"

    if not force_update and redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                # Still increment view count asynchronously or fire-and-forget
                manga = db.session.get(Manga, manga_id)
                if manga:
                    manga.view_count = (manga.view_count or 0) + 1
                    db.session.commit()
                return Response(cached, mimetype='application/json')
        except redis.RedisError as e:
            logger.error(f"Redis error on get {cache_key}: {e}")

    manga = db.session.get(Manga, manga_id)
    if manga:
        manga.view_count = (manga.view_count or 0) + 1
        db.session.commit()

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
            resp_data = {
                'id': manga.id,
                'title': manga.title,
                'cover_url': manga.cover_url,
                'synopsis': manga.synopsis,
                'source': manga.source,
                'chapters': [{'id': c.id.split('/')[-1], 'title': c.title, 'url': c.url} for c in chapters]
            }
            if redis_client:
                try:
                    redis_client.setex(cache_key, 21600, json.dumps(resp_data)) # Cache for 6 hours
                except redis.RedisError as e:
                    logger.error(f"Redis error on set {cache_key}: {e}")
            return jsonify(resp_data)

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

    # Optimize chapter insertion
    existing_chapters = Chapter.query.filter_by(manga_id=manga_id).all()
    existing_ids = {c.id for c in existing_chapters}

    for chap in details['chapters']:
        chap_id = chap['id']
        if chap_id not in existing_ids:
            num = 0.0
            try:
                parts = chap['title'].lower().replace('chapter', '').strip().split()
                if parts: num = float(parts[0].replace('-', '.'))
            except (ValueError, IndexError, AttributeError): pass
            chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=num)
            db.session.add(chapter)
            existing_ids.add(chap_id)

    db.session.commit()

    details['chapters'] = [{'id': c['id'].split('/')[-1], 'title': c['title'], 'url': c['url']} for c in details['chapters']]

    if redis_client:
        try:
            redis_client.setex(cache_key, 21600, json.dumps(details)) # Cache for 6 hours
        except redis.RedisError as e:
            logger.error(f"Redis error on set {cache_key}: {e}")

    return jsonify(details)

@api_bp.route('/chapter/<source>/<path:manga_id>/<chapter_slug>')
async def api_chapter_images(source, manga_id, chapter_slug):
    # Check if we have it locally downloaded first
    base_manga_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'manga')
    try:
        local_dir = get_safe_manga_dir(base_manga_dir, source, manga_id, chapter_slug)
    except ValueError:
        return jsonify({'error': 'Invalid path components'}), 400

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
    except socket.gaierror:
        return "Invalid URL: Cannot resolve host", 400

    allowed_domains = ['aquareader.net', 'wp.com', 'mangadex.org', 'uploads.mangadex.org']
    # Secure external image proxy URLs with strict domain validation
    if not any(hostname == domain or hostname.endswith('.' + domain) for domain in allowed_domains):
        return "Domain not allowed", 403

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
    except requests.exceptions.RequestException as e:
        logger.exception("Failed to proxy image: %s", url)
        return "Failed to fetch image", 500

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
    base_manga_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'manga')
    try:
        local_dir = get_safe_manga_dir(base_manga_dir, source, manga_id, chapter_slug)
    except ValueError:
        return jsonify({'error': 'Invalid path components'}), 400

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

@api_bp.route('/sitemap.xml')
def sitemap():
    base_url = request.host_url.rstrip('/')
    mangas = Manga.query.all()

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    # Add homepage
    xml += f'  <url>\n    <loc>{base_url}</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'

    for manga in mangas:
        loc = f"{base_url}/manga/{manga.source}/{manga.id}"
        lastmod = manga.last_updated.strftime("%Y-%m-%dT%H:%M:%S+00:00") if manga.last_updated else ""
        xml += f'  <url>\n    <loc>{loc}</loc>\n'
        if lastmod:
            xml += f'    <lastmod>{lastmod}</lastmod>\n'
        xml += '    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n'

    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')

@api_bp.route('/robots.txt')
def robots():
    base_url = request.host_url.rstrip('/')
    txt = f"User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /read/\n\nSitemap: {base_url}/api/sitemap.xml"
    return Response(txt, mimetype='text/plain')

# Auth & User Routes
from auth import JWT_SECRET, token_required
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from models import User, Bookmark, ReadingHistory

@api_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing credentials'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'User already exists'}), 409

    hashed = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password_hash=hashed)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing credentials'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not JWT_SECRET:
        return jsonify({'error': 'Server misconfigured. JWT_SECRET missing.'}), 500

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }, JWT_SECRET, algorithm="HS256")

    return jsonify({'token': token, 'username': user.username})

@api_bp.route('/user/bookmarks', methods=['GET', 'POST', 'DELETE'])
@token_required
def handle_bookmarks(current_user):
    if request.method == 'GET':
        bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
        if not bookmarks:
            return jsonify([])

        manga_ids = [b.manga_id for b in bookmarks]
        mangas = Manga.query.filter(Manga.id.in_(manga_ids)).all()
        manga_dict = {m.id: m for m in mangas}

        result = []
        for b in bookmarks:
            manga = manga_dict.get(b.manga_id)
            if manga:
                result.append({
                    'manga_id': manga.id,
                    'title': manga.title,
                    'cover_url': manga.cover_url,
                    'source': manga.source
                })
        return jsonify(result)

    elif request.method == 'POST':
        manga_id = request.json.get('manga_id')
        if not manga_id: return jsonify({'error': 'missing manga_id'}), 400

        if Bookmark.query.filter_by(user_id=current_user.id, manga_id=manga_id).first():
            return jsonify({'message': 'Already bookmarked'}), 200

        new_bm = Bookmark(user_id=current_user.id, manga_id=manga_id)
        db.session.add(new_bm)
        db.session.commit()
        return jsonify({'message': 'Bookmarked added'}), 201

    elif request.method == 'DELETE':
        manga_id = request.json.get('manga_id')
        bm = Bookmark.query.filter_by(user_id=current_user.id, manga_id=manga_id).first()
        if bm:
            db.session.delete(bm)
            db.session.commit()
        return jsonify({'message': 'Bookmark removed'}), 200

@api_bp.route('/user/history', methods=['GET', 'POST'])
@token_required
def handle_history(current_user):
    if request.method == 'GET':
        history = ReadingHistory.query.filter_by(user_id=current_user.id).order_by(ReadingHistory.last_read.desc()).limit(20).all()
        if not history:
            return jsonify([])

        manga_ids = [h.manga_id for h in history]
        mangas = Manga.query.filter(Manga.id.in_(manga_ids)).all()
        manga_dict = {m.id: m for m in mangas}

        result = []
        for h in history:
            manga = manga_dict.get(h.manga_id)
            if manga:
                result.append({
                    'manga_id': manga.id,
                    'title': manga.title,
                    'source': manga.source,
                    'chapter_id': h.chapter_id,
                    'last_read': h.last_read.isoformat()
                })
        return jsonify(result)

    elif request.method == 'POST':
        data = request.json
        if not data or not data.get('manga_id') or not data.get('chapter_id'):
            return jsonify({'error': 'Missing fields'}), 400

        history = ReadingHistory.query.filter_by(user_id=current_user.id, manga_id=data['manga_id']).first()
        if history:
            history.chapter_id = data['chapter_id']
            history.last_read = datetime.now(timezone.utc)
        else:
            history = ReadingHistory(user_id=current_user.id, manga_id=data['manga_id'], chapter_id=data['chapter_id'])
            db.session.add(history)

        db.session.commit()
        return jsonify({'message': 'History updated'}), 200