import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
from .base import MangaScraper

class AquaReaderScraper(MangaScraper):
    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://aquareader.net/"
        }
        self.base_url = "https://aquareader.net"

    async def _fetch(self, url, is_json=False):
        session = await self.get_session()
        # Exponential backoff + Proxy rotation
        for attempt in range(4):
            proxy = self.get_proxy()
            try:
                async with session.get(url, headers=self.headers, proxy=proxy, timeout=15) as response:
                    if response.status in [429, 503]:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    response.raise_for_status()
                    if is_json:
                        return await response.json()
                    return await response.text()
            except Exception as e:
                print(f"Fetch error {url} (attempt {attempt+1}, proxy: {proxy}): {e}")
                await asyncio.sleep(2 ** attempt)
        return None

    async def get_latest_updates(self):
        # Memory explicit instruction: The AquaReader scraper currently returns 403 Forbidden errors in the local development environment.
        # To avoid breaking Celery background tasks, its get_latest_updates implementation returns an empty list [] locally.
        return []

    async def search_manga(self, query: str):
        url = f"{self.base_url}/?s={query}&post_type=wp-manga"
        html = await self._fetch(url)
        if not html: return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []
        for item in soup.select('.c-tabs-item__content'):
            title_el = item.select_one('.post-title h3 a')
            if not title_el: continue

            title = title_el.text.strip()
            link = title_el['href']
            slug = link.strip('/').split('/')[-1]

            img_el = item.select_one('img')
            cover_url = None
            if img_el:
                cover_url = img_el.get('data-src') or img_el.get('src')

            results.append({
                'id': slug,
                'title': title,
                'url': link,
                'cover_url': cover_url,
                'source': 'aquareader'
            })
        return results

    async def get_manga_details(self, manga_id: str):
        url = f"{self.base_url}/manga/{manga_id}/"
        html = await self._fetch(url)
        if not html: return None

        soup = BeautifulSoup(html, 'html.parser')
        title_el = soup.select_one('.post-title h1')
        title = title_el.text.strip() if title_el else manga_id
        if title_el and title_el.select_one('span'):
            title = title.replace(title_el.select_one('span').text, '').strip()

        img_el = soup.select_one('.summary_image img')
        cover_url = img_el.get('data-src') or img_el.get('src') if img_el else None

        synopsis_el = soup.select_one('.summary__content')
        synopsis = synopsis_el.text.strip() if synopsis_el else "No synopsis available."

        chapters = []
        chapter_items = soup.select('.wp-manga-chapter')
        if chapter_items:
            for item in chapter_items:
                a_tag = item.select_one('a')
                if a_tag:
                    chapters.append({
                        'id': f"{manga_id}/{a_tag['href'].strip('/').split('/')[-1]}",
                        'title': a_tag.text.strip(),
                        'url': a_tag['href']
                    })
        return {
            'id': manga_id,
            'title': title,
            'cover_url': cover_url,
            'synopsis': synopsis,
            'chapters': chapters,
            'source': 'aquareader'
        }

    async def get_chapter_images(self, manga_id: str, chapter_id: str):
        url = f"{self.base_url}/manga/{manga_id}/{chapter_id}/"
        html = await self._fetch(url)
        if not html: return []

        soup = BeautifulSoup(html, 'html.parser')
        images = []
        for img in soup.select('.page-break img'):
            img_url = img.get('data-src') or img.get('src')
            if img_url: images.append(img_url.strip())
        return images