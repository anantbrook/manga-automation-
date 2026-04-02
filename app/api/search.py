from flask import Blueprint, jsonify, request
import os
import asyncio
from app.models import db
from app.models.manga import Manga
from sqlalchemy import or_
from app.scraper.factory import ScraperFactory
from app.tasks.scraper_tasks import fetch_and_add_manga_from_url

search_bp = Blueprint('search', __name__)

@search_bp.route('/', methods=['GET'])
def search_manga():
    q = request.args.get('q', '')
    if not q:
        return jsonify([])

    # Since multi-source search can be slow, we will search local DB first.
    # We will trigger a background job to scrape AquaReader for now to match old behavior.

    # Check local DB
    mangas = Manga.query.filter(or_(Manga.title.ilike(f'%{q}%'), Manga.id.ilike(f'%{q}%'))).all()
    results = [{"id": m.id, "title": m.title, "cover_url": m.cover_url, "source": m.source} for m in mangas]

    # Quick async fetch from Aquareader (original behavior)
    async def fetch_aquareader_search():
        from app.scraper.aquareader import AquaReaderScraper
        from bs4 import BeautifulSoup
        scraper = AquaReaderScraper()
        url = f"https://aquareader.net/?s={q}&post_type=wp-manga"
        html = await scraper.fetch_html(url)
        live_results = []
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.find_all('div', class_='row c-tabs-item__content'):
                title_tag = item.find('h3', class_='h4').find('a') if item.find('h3', class_='h4') else None
                if not title_tag:
                    continue
                title = title_tag.text.strip()
                url_tag = title_tag['href']
                manga_id = url_tag.strip('/').split('/')[-1]

                img_tag = item.find('div', class_='tab-thumb').find('img') if item.find('div', class_='tab-thumb') else None
                cover_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ''

                live_results.append({
                    "id": manga_id,
                    "title": title,
                    "cover_url": cover_url,
                    "source": "aquareader"
                })
        return live_results

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        live_res = loop.run_until_complete(fetch_aquareader_search())

        # Merge results, avoiding duplicates by ID
        existing_ids = {m['id'] for m in results}
        for res in live_res:
            if res['id'] not in existing_ids:
                results.append(res)
                # Background cache it
                fetch_and_add_manga_from_url.delay(f"https://aquareader.net/manga/{res['id']}")

    except Exception as e:
        print(f"Error fetching live search: {e}")

    return jsonify(results)
