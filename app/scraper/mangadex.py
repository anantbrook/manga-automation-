from app.scraper.base import MangaScraper
import re

class MangaDexScraper(MangaScraper):
    def __init__(self):
        super().__init__()
        self.api_base = "https://api.mangadex.org"

    def is_supported(self, url):
        return "mangadex.org" in url

    def extract_manga_id_from_url(self, url):
        # https://mangadex.org/title/32d76d19-8a05-4db0-9fc2-e0b0648fe9d0/solo-leveling
        if '/title/' in url:
            parts = url.split('/title/')
            if len(parts) > 1:
                return parts[1].split('/')[0]
        return None

    async def parse_url_to_manga(self, url):
        manga_id = self.extract_manga_id_from_url(url)
        if not manga_id:
            return None
        return await self.get_manga_details(manga_id)

    async def get_manga_details(self, manga_id):
        url = f"{self.api_base}/manga/{manga_id}?includes[]=cover_art"
        data = await self.fetch_json(url)
        if not data or data.get('result') != 'ok':
            return None

        manga_data = data['data']
        title = manga_data['attributes']['title'].get('en') or list(manga_data['attributes']['title'].values())[0]
        synopsis = manga_data['attributes']['description'].get('en') or list(manga_data['attributes']['description'].values())[0]

        cover_url = ""
        for rel in manga_data['relationships']:
            if rel['type'] == 'cover_art':
                file_name = rel['attributes']['fileName']
                cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{file_name}"
                break

        # Fetch chapters
        chap_url = f"{self.api_base}/manga/{manga_id}/feed?translatedLanguage[]=en&order[chapter]=desc&limit=500"
        chap_data = await self.fetch_json(chap_url)
        chapters = []
        if chap_data and chap_data.get('result') == 'ok':
            for c in chap_data['data']:
                chap_id = c['id']
                chap_num = c['attributes']['chapter']
                chap_title = c['attributes']['title'] or f"Chapter {chap_num}"

                num = 0.0
                try:
                    num = float(chap_num)
                except:
                    pass

                chapters.append({
                    "id": f"{manga_id}/{chap_id}",
                    "title": chap_title,
                    "url": f"https://mangadex.org/chapter/{chap_id}",
                    "number": num
                })

        return {
            "id": manga_id,
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "chapters": chapters,
            "source": "mangadex"
        }

    async def get_chapter_images(self, chapter_url):
        # We need the chapter ID
        # https://mangadex.org/chapter/6ebdfd43-ebdb-4720-9a4f-5fc7a1db3ad4
        chap_id = chapter_url.strip('/').split('/')[-1]

        # 1. Fetch the chapter info to get the hash
        url = f"{self.api_base}/at-home/server/{chap_id}"
        data = await self.fetch_json(url)
        if not data or data.get('result') != 'ok':
            return []

        base_url = data['baseUrl']
        chap_hash = data['chapter']['hash']
        data_arr = data['chapter']['data']

        images = []
        for file in data_arr:
            images.append(f"{base_url}/data/{chap_hash}/{file}")

        return images
