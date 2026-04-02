from bs4 import BeautifulSoup
from app.scraper.base import MangaScraper
import re
from urllib.parse import urlparse, unquote

class AsuraScansScraper(MangaScraper):
    def __init__(self):
        super().__init__()
        # Asura Scans changes domains frequently, so we support any that match the pattern
        self.supported_domains = ["asuracomic.net", "asuratoon.com", "asura.gg"]

    def is_supported(self, url):
        return any(domain in url for domain in self.supported_domains)

    def extract_manga_id_from_url(self, url):
        # https://asuracomic.net/manga/solo-leveling
        if '/manga/' in url:
            parts = url.split('/manga/')
            if len(parts) > 1:
                return parts[-1].strip('/').split('?')[0]
        # or https://asuracomic.net/series/solo-leveling
        elif '/series/' in url:
            parts = url.split('/series/')
            if len(parts) > 1:
                return parts[-1].strip('/').split('?')[0]
        return None

    async def parse_url_to_manga(self, url):
        manga_id = self.extract_manga_id_from_url(url)
        if not manga_id:
            return None
        return await self.get_manga_details(url)

    async def get_manga_details(self, url):
        html = await self.fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # This selector depends heavily on the current Asura theme, which uses Tailwind mostly.
        # Often the title is an H1.
        title_tag = soup.find('h1')
        if not title_tag:
            return None
        title = title_tag.text.strip()

        # Find cover image. Often has itemprop="image" or is the first large image
        img_tag = soup.find('img', {'itemprop': 'image'})
        cover_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ''

        # Synopsis
        synopsis_div = soup.find('div', {'itemprop': 'description'})
        synopsis = synopsis_div.text.strip() if synopsis_div else "No synopsis available."

        # Extract Chapters. Asura usually has a chapter list div with lots of <a> tags
        chapters = []
        chap_list = soup.find('div', class_=re.compile(r'eplister|chapterlist'))
        if chap_list:
            for a_tag in chap_list.find_all('a'):
                chap_title = a_tag.text.strip()
                chap_url = a_tag['href']

                # e.g., https://asuracomic.net/manga/solo-leveling-chapter-1
                slug = chap_url.strip('/').split('/')[-1]

                num = 0.0
                try:
                    num_match = re.search(r'chapter[ -](\d+(?:\.\d+)?)', chap_url, re.IGNORECASE)
                    if num_match:
                        num = float(num_match.group(1))
                except:
                    pass

                # Assuming manga_id is extracted from the base URL provided to this function
                manga_id = self.extract_manga_id_from_url(url) or "unknown"
                chapters.append({
                    "id": f"{manga_id}/{slug}",
                    "title": chap_title,
                    "url": chap_url,
                    "number": num
                })

        return {
            "id": self.extract_manga_id_from_url(url) or "unknown",
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "chapters": chapters,
            "source": "asurascans"
        }

    async def get_chapter_images(self, chapter_url):
        html = await self.fetch_html(chapter_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        # Asura reader typically has images inside an id "readerarea"
        reader_area = soup.find('div', id='readerarea')
        if not reader_area:
            return []

        images = []
        for img in reader_area.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src and not src.endswith('blank.gif') and 'discord' not in src.lower():
                images.append(src.strip())

        return images
