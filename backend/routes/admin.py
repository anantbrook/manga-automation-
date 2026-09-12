from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from models import db, Manga, Chapter
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_authorized():
    token = request.cookies.get('admin_token')
    try:
        return token == os.environ['ADMIN_TOKEN']
    except KeyError:
        return False

@admin_bp.route('/login', methods=['GET'])
def admin_login():
    return render_template('admin_login.html')

@admin_bp.route('/login', methods=['POST'])
def admin_login_post():
    token = request.form.get('token')
    try:
        if token == os.environ['ADMIN_TOKEN']:
            resp = make_response(redirect(url_for('admin.admin_panel')))
            resp.set_cookie('admin_token', token, httponly=True)
            return resp
    except KeyError:
        pass

    flash("Invalid token")
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/logout')
def admin_logout():
    resp = make_response(redirect(url_for('admin.admin_login')))
    resp.delete_cookie('admin_token')
    return resp

@admin_bp.route('/')
def admin_panel():
    if not is_authorized():
        return redirect(url_for('admin.admin_login'))

    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    return render_template('admin.html', mangas=mangas, chapter_count=chapters)

@admin_bp.route('/add', methods=['POST'])
async def admin_add():
    if not is_authorized():
        return redirect(url_for('admin.admin_login'))

    source = request.form.get('source')
    manga_id = request.form.get('manga_id')

    if not source or not manga_id:
        flash("Missing source or manga_id")
        return redirect(url_for('admin.admin_panel'))

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

    flash(f'Manga {manga_id} metadata saved and chapter downloads queued in Celery.')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    if not is_authorized():
        return redirect(url_for('admin.admin_login'))

    manga = db.session.get(Manga, manga_id)
    if manga:
        Chapter.query.filter_by(manga_id=manga_id).delete()
        db.session.delete(manga)
        db.session.commit()

    flash(f'Manga {manga_id} and its chapters removed.')
    return redirect(url_for('admin.admin_panel'))