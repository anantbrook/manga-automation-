from flask import Blueprint, render_template_string, request, jsonify
from models import db, Manga, Chapter
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_authorized():
    token = request.args.get('token')
    try:
        return token == os.environ['ADMIN_TOKEN']
    except KeyError:
        return False

@admin_bp.route('/')
def admin_panel():
    if not is_authorized():
        return "Unauthorized", 401

    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    html = '''
    <html>
    <head><title>MangaFire PRO Admin Panel</title><style>body{font-family:sans-serif; background:#f4f4f4; padding:20px;} table{width:100%; border-collapse:collapse; margin-top:20px;} th,td{padding:10px; border:1px solid #ddd; text-align:left;} th{background:#333;color:white;} .card{background:white; padding:20px; border-radius:8px; box-shadow:0 2px 5px rgba(0,0,0,0.1); margin-bottom:20px;} input, select, button{padding:10px; margin-right:10px; border:1px solid #ccc; border-radius:4px;}</style></head>
    <body>
        <h1>🔥 MangaFire PRO Admin</h1>

        <div class="card">
            <h3>Add Manga (Trigger Celery Job)</h3>
            <form action="/admin/add?token={{ request.args.get('token') }}" method="post">
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
                    <form action="/admin/delete/{{m.id}}?token={{ request.args.get('token') }}" method="post" style="display:inline;">
                        <button type="submit" style="color:red;">Delete</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, mangas=mangas, chapter_count=chapters, request=request)

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

    existing_chapters = Chapter.query.filter_by(manga_id=manga_id).all()
    existing_chapter_ids = {c.id for c in existing_chapters}

    for chap in details['chapters']:
        chap_id = chap['id']
        if chap_id not in existing_chapter_ids:
            chapter = Chapter(id=chap_id, manga_id=manga_id, title=chap['title'], url=chap['url'], number=0)
            db.session.add(chapter)

            # Queue background download
            download_chapter_images_local.delay(source, manga_id, chap_id.split('/')[-1])

    db.session.commit()

    return f"<script>alert('Manga {manga_id} metadata saved and chapter downloads queued in Celery.'); window.location.href='/admin?token={request.args.get('token')}';</script>"

@admin_bp.route('/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    if not is_authorized():
        return "Unauthorized", 401

    manga = db.session.get(Manga, manga_id)
    if manga:
        Chapter.query.filter_by(manga_id=manga_id).delete()
        db.session.delete(manga)
        db.session.commit()

    return f"<script>alert('Manga {manga_id} and its chapters removed.'); window.location.href='/admin?token={request.args.get('token')}';</script>"