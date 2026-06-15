from flask import Blueprint, render_template, request, jsonify, redirect, url_for, make_response, flash
from models import db, Manga, Chapter
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_authorized(req):
    token = req.cookies.get('admin_token')
    try:
        return token == os.environ['ADMIN_TOKEN']
    except KeyError:
        return False

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        token = request.form.get('admin_token')
        try:
            if token == os.environ['ADMIN_TOKEN']:
                resp = make_response(redirect(url_for('admin.admin_panel')))
                resp.set_cookie('admin_token', token, httponly=True, samesite='Strict')
                return resp
            else:
                flash('Invalid token.')
        except KeyError:
            flash('ADMIN_TOKEN environment variable not set.')
    return render_template('login.html')

@admin_bp.route('/logout')
def admin_logout():
    resp = make_response(redirect(url_for('admin.admin_login')))
    resp.set_cookie('admin_token', '', expires=0)
    return resp

@admin_bp.route('/')
def admin_panel():
    if not is_authorized(request):
        return redirect(url_for('admin.admin_login'))

    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    return render_template('admin.html', mangas=mangas, chapter_count=chapters)

@admin_bp.route('/add', methods=['POST'])
async def admin_add():
    if not is_authorized(request):
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
        flash("Manga not found on source.")
        return redirect(url_for('admin.admin_panel'))

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

    flash(f"Manga {manga_id} metadata saved and chapter downloads queued in Celery.")
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    if not is_authorized(request):
        return redirect(url_for('admin.admin_login'))

    manga = db.session.get(Manga, manga_id)
    if manga:
        Chapter.query.filter_by(manga_id=manga_id).delete()
        db.session.delete(manga)
        db.session.commit()
        flash(f"Manga {manga_id} and its chapters removed.")

    return redirect(url_for('admin.admin_panel'))
