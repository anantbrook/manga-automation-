import aiohttp
import asyncio
from .base import MangaScraper

class MangaDexScraper(MangaScraper):
    def __init__(self):
        super().__init__()
        self.api_url = "https://api.mangadex.org"
        self.uploads_url = "https://uploads.mangadex.org"

    async def _fetch_json(self, url, params=None):
        session = await self.get_session()
        for _ in range(3):
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 429: # Rate limited
                        await asyncio.sleep(2)
                        continue
                    response.raise_for_status()
                    return await response.json()
            except Exception as e:
                print(f"MangaDex Error {url}: {e}")
                await asyncio.sleep(1)
        return None

    async def search_manga(self, query: str):
        url = f"{self.api_url}/manga"
        params = {"title": query, "includes[]": "cover_art", "limit": 15}
        data = await self._fetch_json(url, params)
        if not data or 'data' not in data: return []

        results = []
        for item in data['data']:
            title = item['attributes']['title'].get('en') or list(item['attributes']['title'].values())[0]
            manga_id = item['id']

            cover_filename = None
            for rel in item['relationships']:
                if rel['type'] == 'cover_art' and 'attributes' in rel:
                    cover_filename = rel['attributes'].get('fileName')

            cover_url = f"{self.uploads_url}/covers/{manga_id}/{cover_filename}" if cover_filename else None

            results.append({
                'id': manga_id,
                'title': title,
                'url': f"https://mangadex.org/title/{manga_id}",
                'cover_url': cover_url,
                'source': 'mangadex'
            })
        return results

    async def get_manga_details(self, manga_id: str):
        url = f"{self.api_url}/manga/{manga_id}"
        params = {"includes[]": "cover_art"}
        data = await self._fetch_json(url, params)
        if not data or 'data' not in data: return None

        item = data['data']
        title = item['attributes']['title'].get('en') or list(item['attributes']['title'].values())[0]
        synopsis = item['attributes']['description'].get('en', 'No synopsis available.')

        cover_filename = None
        for rel in item['relationships']:
            if rel['type'] == 'cover_art' and 'attributes' in rel:
                cover_filename = rel['attributes'].get('fileName')
        cover_url = f"{self.uploads_url}/covers/{manga_id}/{cover_filename}" if cover_filename else None

        # Fetch English chapters
        feed_url = f"{self.api_url}/manga/{manga_id}/feed"
        feed_params = {"translatedLanguage[]": ["en"], "order[chapter]": "desc", "limit": 100}
        feed_data = await self._fetch_json(feed_url, feed_params)

        chapters = []
        if feed_data and 'data' in feed_data:
            for c in feed_data['data']:
                ch_num = c['attributes'].get('chapter') or '0'
                chapters.append({
                    'id': f"{manga_id}/{c['id']}",
                    'title': f"Chapter {ch_num}",
                    'url': f"https://mangadex.org/chapter/{c['id']}"
                })

        return {
            'id': manga_id,
            'title': title,
            'cover_url': cover_url,
            'synopsis': synopsis,
            'chapters': chapters,
            'source': 'mangadex'
        }

    async def get_chapter_images(self, manga_id: str, chapter_id: str):
        # In mangadex, the chapter_id is actually the MD chapter uuid
        md_chap_id = chapter_id.split('/')[-1] if '/' in chapter_id else chapter_id

        url = f"{self.api_url}/at-home/server/{md_chap_id}"
        data = await self._fetch_json(url)
        if not data or 'chapter' not in data: return []

        base = data['baseUrl']
        hash_val = data['chapter']['hash']
        images = []

        for filename in data['chapter']['data']:
            images.append(f"{base}/data/{hash_val}/{filename}")

        return images

    async def get_latest_updates(self):
        url = f"{self.api_url}/manga"
        params = {
            "includes[]": "cover_art",
            "limit": 20,
            "order[latestUploadedChapter]": "desc"
        }
        data = await self._fetch_json(url, params)
        if not data or 'data' not in data: return []

        results = []
        for item in data['data']:
            title = item['attributes']['title'].get('en') or list(item['attributes']['title'].values())[0]
            manga_id = item['id']

            cover_filename = None
            for rel in item['relationships']:
                if rel['type'] == 'cover_art' and 'attributes' in rel:
                    cover_filename = rel['attributes'].get('fileName')

            cover_url = f"{self.uploads_url}/covers/{manga_id}/{cover_filename}" if cover_filename else None

            results.append({
                'id': manga_id,
                'title': title,
                'url': f"https://mangadex.org/title/{manga_id}",
                'cover_url': cover_url,
                'source': 'mangadex'
            })
        return results