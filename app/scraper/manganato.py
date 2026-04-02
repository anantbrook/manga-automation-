from bs4 import BeautifulSoup
from app.scraper.base import MangaScraper
import re

class ManganatoScraper(MangaScraper):
    def __init__(self):
        super().__init__()
        self.base_urls = ["https://manganato.com", "https://chapmanganato.com"]

    def is_supported(self, url):
        return any(domain in url for domain in self.base_urls)

    def extract_manga_id_from_url(self, url):
        # https://manganato.com/manga-pq993356
        if '/manga-' in url:
            return url.split('/manga-')[-1].split('?')[0]
        elif '/manga-' in url:
            return url.split('/manga-')[-1].split('?')[0]
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

        info_div = soup.find('div', class_='panel-story-info')
        if not info_div:
            return None

        title = info_div.find('h1').text.strip()
        img_tag = info_div.find('span', class_='info-image').find('img')
        cover_url = img_tag['src'] if img_tag else ''

        synopsis_div = info_div.find('div', id='panel-story-info-description')
        synopsis = synopsis_div.text.strip().replace('Description :', '').strip() if synopsis_div else "No synopsis available."

        # Chapters
        chapters = []
        chap_list = soup.find('ul', class_='row-content-chapter')
        if chap_list:
            for li in chap_list.find_all('li', class_='a-h'):
                a_tag = li.find('a')
                if not a_tag:
                    continue
                chap_title = a_tag.text.strip()
                chap_url = a_tag['href']

                # e.g., https://chapmanganato.com/manga-pq993356/chapter-1
                slug = chap_url.strip('/').split('/')[-1]

                num = 0.0
                try:
                    num_match = re.search(r'chapter[ -](\d+(?:\.\d+)?)', chap_url, re.IGNORECASE)
                    if num_match:
                        num = float(num_match.group(1))
                except:
                    pass

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
            "source": "manganato"
        }

    async def get_chapter_images(self, chapter_url):
        html = await self.fetch_html(chapter_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        reader_area = soup.find('div', class_='container-chapter-reader')
        if not reader_area:
            return []

        images = []
        for img in reader_area.find_all('img'):
            src = img.get('src')
            if src:
                images.append(src.strip())

        return images
