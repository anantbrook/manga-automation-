import sys
import io
import os
import zipfile
import threading
from datetime import datetime
from flask import Flask, jsonify, request, send_file, render_template, Response
from flask_sqlalchemy import SQLAlchemy
import requests
from scraper import search_manga, get_manga_details, get_chapter_images

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///manga.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Manga(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    cover_url = db.Column(db.String(512))
    synopsis = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Chapter(db.Model):
    id = db.Column(db.String(255), primary_key=True) # Format: manga_id/chapter_slug
    manga_id = db.Column(db.String(255), db.ForeignKey('manga.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    # Order for sorting natively
    number = db.Column(db.Float, default=0)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    if not q:
        return jsonify([])

    # Check DB first? Search usually relies on live results unless we fully index.
    # For now, let's just do a live search and optionally cache results.
    results = search_manga(q)

    # Background cache update
    def cache_results(results_list):
        with app.app_context():
            for res in results_list:
                manga = db.session.get(Manga, res['id'])
                if not manga:
                    manga = Manga(id=res['id'], title=res['title'], cover_url=res['cover_url'])
                    db.session.add(manga)
                else:
                    manga.title = res['title']
                    if res['cover_url']:
                        manga.cover_url = res['cover_url']
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error caching search results: {e}")

    if results:
        threading.Thread(target=cache_results, args=(results,)).start()

    return jsonify(results)

@app.route('/api/manga/<path:manga_id>')
def api_manga_details(manga_id):
    # Try DB first
    manga = db.session.get(Manga, manga_id)
    force_update = request.args.get('force', 'false').lower() == 'true'

    if manga and not force_update and manga.synopsis:
        # Check if chapters are cached
        chapters = Chapter.query.filter_by(manga_id=manga_id).all()
        if chapters:
            return jsonify({
                'id': manga.id,
                'title': manga.title,
                'cover_url': manga.cover_url,
                'synopsis': manga.synopsis,
                'chapters': [{'id': c.id, 'title': c.title, 'url': c.url} for c in chapters]
            })

    # If not in DB or force update, scrape
    details = get_manga_details(manga_id)
    if not details:
        return jsonify({'error': 'Not found'}), 404

    # Update DB
    if not manga:
        manga = Manga(id=details['id'], title=details['title'])
        db.session.add(manga)

    manga.cover_url = details['cover_url']
    manga.synopsis = details['synopsis']
    manga.last_updated = datetime.utcnow()

    # Update chapters
    for chap in details['chapters']:
        chapter = db.session.get(Chapter, chap['id'])
        if not chapter:
            # Try to extract chapter number for sorting
            num = 0.0
            try:
                # "Chapter 1", "Chapter 1.5", etc.
                parts = chap['title'].lower().replace('chapter', '').strip().split()
                if parts:
                    num = float(parts[0].replace('-', '.'))
            except:
                pass

            chapter = Chapter(id=chap['id'], manga_id=manga_id, title=chap['title'], url=chap['url'], number=num)
            db.session.add(chapter)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error caching manga details: {e}")

    return jsonify(details)

@app.route('/api/chapter/<path:manga_id>/<chapter_slug>')
def api_chapter_images(manga_id, chapter_slug):
    images = get_chapter_images(manga_id, chapter_slug)
    if not images:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'images': images})

@app.route('/api/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url:
        return "No url provided", 400

    # Security block: SSRF protection
    # Ensure the requested URL goes to the expected domains only
    allowed_domains = ['aquareader.net', 'wp.com', 'manga']
    if not any(domain in url for domain in allowed_domains):
        # We also want to allow standard image hosts that the scraper might return.
        # But to be completely safe against SSRF to internal network:
        if url.startswith('http://127.') or url.startswith('http://localhost') or url.startswith('http://10.') or url.startswith('http://192.168.') or url.startswith('http://172.'):
            return "Invalid URL", 403

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://aquareader.net/"
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

@app.route('/api/download/<path:manga_id>/<chapter_slug>')
def api_download_chapter(manga_id, chapter_slug):
    images = get_chapter_images(manga_id, chapter_slug)
    if not images:
        return "Images not found", 404

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://aquareader.net/"
        }
        for idx, img_url in enumerate(images):
            try:
                img_data = requests.get(img_url, headers=headers).content
                ext = img_url.split('.')[-1].split('?')[0]
                if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                    ext = 'jpg'
                filename = f"{idx:03d}.{ext}"
                zf.writestr(filename, img_data)
            except Exception as e:
                print(f"Failed to download image {idx}: {e}")

    memory_file.seek(0)
    return send_file(memory_file,
                     download_name=f"{manga_id}-{chapter_slug}.cbz",
                     as_attachment=True)


@app.route('/admin')
def admin_panel():
    # Admin must be authenticated. Since it's a basic app without sessions, let's use simple query param auth.
    admin_token = request.args.get('token')
    if admin_token != os.environ.get('ADMIN_TOKEN', 'admin123'):
        return "Unauthorized", 401

    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    html = '''
    <html>
    <head><title>Admin Panel</title><style>body{font-family:sans-serif; background:#f4f4f4; padding:20px;} table{width:100%; border-collapse:collapse;} th,td{padding:10px; border:1px solid #ddd; text-align:left;} th{background:#333;color:white;}</style></head>
    <body>
        <h1>Admin Dashboard</h1>
        <p>Total Cached Manga: <b>{{ mangas|length }}</b></p>
        <p>Total Cached Chapters: <b>{{ chapter_count }}</b></p>

        <h2>Cached Manga Database</h2>
        <table>
            <tr><th>ID</th><th>Title</th><th>Last Updated</th><th>Action</th></tr>
            {% for m in mangas %}
            <tr>
                <td>{{ m.id }}</td>
                <td>{{ m.title }}</td>
                <td>{{ m.last_updated }}</td>
                <td>
                    <form action="/admin/delete/{{m.id}}?token={{ request.args.get('token') }}" method="post" style="display:inline;">
                        <button type="submit" style="color:red;">Delete (DMCA)</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, mangas=mangas, chapter_count=chapters)

from flask import render_template_string

@app.route('/admin/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    admin_token = request.args.get('token')
    if admin_token != os.environ.get('ADMIN_TOKEN', 'admin123'):
        return "Unauthorized", 401

    # DMCA removal feature
    manga = db.session.get(Manga, manga_id)
    if manga:
        Chapter.query.filter_by(manga_id=manga_id).delete()
        db.session.delete(manga)
        db.session.commit()
    return f"<script>alert('Manga {manga_id} and its chapters removed.'); window.location.href='/admin';</script>"

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
