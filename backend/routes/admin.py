from flask import Blueprint, render_template_string, request, jsonify, make_response, redirect, url_for, flash
from models import db, Manga, Chapter
import os
import urllib.parse
from markupsafe import escape

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_authorized():
    token = request.cookies.get('admin_token')
    try:
        return token == os.environ['ADMIN_TOKEN']
    except KeyError:
        return False

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        token = request.form.get('token')
        try:
            if token == os.environ['ADMIN_TOKEN']:
                resp = make_response(redirect(url_for('admin.admin_panel')))
                resp.set_cookie('admin_token', token, httponly=True, secure=False) # In production secure=True
                return resp
            else:
                return "Invalid token", 401
        except KeyError:
            return "Server misconfiguration", 500

    html = '''
    <html>
    <head><title>Admin Login</title></head>
    <body>
        <h2>Admin Login</h2>
        <form action="/admin/login" method="post">
            <input type="password" name="token" placeholder="Admin Token" required>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    '''
    return render_template_string(html)

@admin_bp.route('/')
def admin_panel():
    if not is_authorized():
        return redirect(url_for('admin.admin_login'))

    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    message = request.args.get('message', '')

    html = '''
    <html>
    <head><title>MangaFire PRO Admin Panel</title><style>body{font-family:sans-serif; background:#f4f4f4; padding:20px;} table{width:100%; border-collapse:collapse; margin-top:20px;} th,td{padding:10px; border:1px solid #ddd; text-align:left;} th{background:#333;color:white;} .card{background:white; padding:20px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1); margin-bottom:20px;} input, select, button{padding:10px; margin-right:10px; border:1px solid #ccc; border-radius:4px;} .message {background: #d4edda; color: #155724; padding: 10px; border: 1px solid #c3e6cb; border-radius: 4px; margin-bottom: 20px;}</style></head>
    <body>
        <h1>🔥 MangaFire PRO Admin</h1>
        {% if message %}
            <div class="message">{{ message }}</div>
        {% endif %}

        <div class="card">
            <h3>Add Manga (Trigger Celery Job)</h3>
            <form action="/admin/add" method="post">
                <select name="source">
                    <option value="mangadex">MangaDex</option>
                    <option value="aquareader">AquaReader</option>
                </select>
                <input type="text" name="manga_id" placeholder="Enter Manga ID/Slug" required style="width:300px;">
                <button type="submit" style="background:#ff3300; color:white; border:none; cursor:pointer;">Fetch & Cache Everything</button>
            </form>
        </div>

        <div class="card">
            <p>Total Cached Manga: <b>{{ mangas|length }}</b></p>
            <p>Total Cached Chapters: <b>{{ chapter_count }}</b></p>
        </div>

        <h2>Cached Manga Database</h2>
        <table>
            <tr><th>Source</th><th>ID</th><th>Title</th><th>Last Updated</th><th>Action</th></tr>
            {% for m in mangas %}
            <tr>
                <td>{{ m.source }}</td>
                <td>{{ m.id }}</td>
                <td>{{ m.title }}</td>
                <td>{{ m.last_updated }}</td>
                <td>
                    <form action="/admin/delete/{{m.id}}" method="post" style="display:inline;">
                        <button type="submit" style="color:red;">Delete</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, mangas=mangas, chapter_count=chapters, message=message)

@admin_bp.route('/add', methods=['POST'])
async def admin_add():
    if not is_authorized():
        return "Unauthorized", 401

    source = request.form.get('source')
    manga_id = request.form.get('manga_id')

    if not source or not manga_id:
        return "Missing source or manga_id", 400

    from tasks import download_chapter_images_local
    import asyncio
    from scrapers import get_scraper

    # 1. Scrape it so it hits the DB
    scraper = get_scraper(source)
    details = await scraper.get_manga_details(manga_id)

    if not details:
        return "Manga not found on source.", 404

    # Create DB entry if not exists
    manga = db.session.get(Manga, manga_id)
    if not manga:
        manga = Manga(id=details['id'], title=details['title'], source=source)
        db.session.add(manga)

    manga.cover_url = details['cover_url']
    manga.synopsis = details['synopsis']

    for chap in details['chapters']:
        chap_id = chap['id']
        chapter = db.session.get(Chapter, chap_id)
        if not chapter:
            chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=0)
            db.session.add(chapter)

            # Queue background download
            download_chapter_images_local.delay(source, manga_id, chap_id.split('/')[-1])

    db.session.commit()

    safe_manga_id = escape(manga_id)
    msg = f"Manga {safe_manga_id} metadata saved and chapter downloads queued in Celery."
    return redirect(url_for('admin.admin_panel', message=msg))

@admin_bp.route('/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    if not is_authorized():
        return "Unauthorized", 401

    manga = db.session.get(Manga, manga_id)
    if manga:
        Chapter.query.filter_by(manga_id=manga_id).delete()
        db.session.delete(manga)
        db.session.commit()

    safe_manga_id = escape(manga_id)
    msg = f"Manga {safe_manga_id} and its chapters removed."
    return redirect(url_for('admin.admin_panel', message=msg))