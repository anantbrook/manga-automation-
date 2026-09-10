from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Manga, Chapter
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_authorized():
    # Use secure HttpOnly cookies/sessions instead of URL parameters
    return session.get('admin_logged_in') == True

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        token = request.form.get('admin_token')
        expected_token = os.environ.get('ADMIN_TOKEN')

        if expected_token and token == expected_token:
            session['admin_logged_in'] = True
            return redirect(url_for('admin.admin_panel'))
        else:
            flash('Invalid admin token.', 'error')

    return render_template('admin_login.html')

@admin_bp.route('/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/')
def admin_panel():
    if not is_authorized():
        return redirect(url_for('admin.admin_login'))

    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    return render_template('admin_panel.html', mangas=mangas, chapter_count=chapters)

@admin_bp.route('/add', methods=['POST'])
async def admin_add():
    if not is_authorized():
        return redirect(url_for('admin.admin_login'))

    source = request.form.get('source')
    manga_id = request.form.get('manga_id')

    if not source or not manga_id:
        flash("Missing source or manga_id", "error")
        return redirect(url_for('admin.admin_panel'))

    from tasks import download_chapter_images_local
    import asyncio
    from scrapers import get_scraper

    # 1. Scrape it so it hits the DB
    scraper = get_scraper(source)
    details = await scraper.get_manga_details(manga_id)

    if not details:
        flash("Manga not found on source.", "error")
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

    flash(f"Manga {manga_id} metadata saved and chapter downloads queued in Celery.", "success")
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

    flash(f"Manga {manga_id} and its chapters removed.", "success")
    return redirect(url_for('admin.admin_panel'))