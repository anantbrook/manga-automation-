import os
from flask import Blueprint, render_template_string, request, redirect, url_for, jsonify
from app.models import db
from app.models.manga import Manga
from app.models.chapter import Chapter
from app.core.config import Config
from app.tasks.scraper_tasks import fetch_and_add_manga_from_url

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def check_auth(token):
    return token == Config.ADMIN_TOKEN

@admin_bp.route('/', methods=['GET', 'POST'])
def admin_panel():
    token = request.args.get('token')
    if not check_auth(token):
        return "Unauthorized", 401

    if request.method == 'POST':
        # Admin is adding a new manga via URL
        url = request.form.get('url')
        if url:
            # Trigger background job to parse, scrape and download
            task = fetch_and_add_manga_from_url.delay(url)
            message = f"Background task {task.id} started to fetch {url}"
            return redirect(url_for('admin.admin_panel', token=token, msg=message))

    mangas = Manga.query.all()
    chapter_count = Chapter.query.count()
    msg = request.args.get('msg', '')

    html = '''
    <html>
    <head><title>Admin Panel - MangaFire Pro</title>
    <style>
    body{font-family:sans-serif; background:#121212; color:#fff; padding:20px;}
    table{width:100%; border-collapse:collapse; margin-top:20px;}
    th,td{padding:10px; border:1px solid #444; text-align:left;}
    th{background:#ff4500;color:white;}
    .container { max-width: 1200px; margin: auto; }
    input[type="text"] { width: 60%; padding: 10px; }
    button { padding: 10px 20px; background:#ff4500; color:white; border:none; cursor:pointer;}
    .msg { color: #0f0; margin-bottom: 20px; }
    </style></head>
    <body>
        <div class="container">
            <h1>Admin Dashboard - MangaFire Pro</h1>
            {% if msg %}<div class="msg">{{ msg }}</div>{% endif %}

            <div style="background:#222; padding: 20px; margin-bottom: 20px;">
                <h2>Add Manga Manually (Trigger Auto-Downloader)</h2>
                <form method="post" action="?token={{ request.args.get('token') }}">
                    <input type="text" name="url" placeholder="Paste supported URL (Asura, MangaDex, Manganato, AquaReader)" required>
                    <button type="submit">Add & Download</button>
                </form>
            </div>

            <p>Total Cached Manga: <b>{{ mangas|length }}</b></p>
            <p>Total Cached Chapters: <b>{{ chapter_count }}</b></p>

            <h2>Cached Manga Database</h2>
            <table>
                <tr><th>ID</th><th>Title</th><th>Source</th><th>Last Updated</th><th>Action</th></tr>
                {% for m in mangas %}
                <tr>
                    <td>{{ m.id }}</td>
                    <td>{{ m.title }}</td>
                    <td>{{ m.source }}</td>
                    <td>{{ m.last_updated }}</td>
                    <td>
                        <form action="{{ url_for('admin.admin_delete', manga_id=m.id, token=request.args.get('token')) }}" method="post" style="display:inline;">
                            <button type="submit" style="background:#dc143c;">Delete (DMCA)</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, mangas=mangas, chapter_count=chapter_count, msg=msg)

@admin_bp.route('/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    token = request.args.get('token')
    if not check_auth(token):
        return "Unauthorized", 401

    manga = db.session.get(Manga, manga_id)
    if manga:
        db.session.delete(manga)
        db.session.commit()
    return redirect(url_for('admin.admin_panel', token=token, msg=f"Manga {manga_id} deleted."))
