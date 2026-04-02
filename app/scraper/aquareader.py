from bs4 import BeautifulSoup
from app.scraper.base import MangaScraper
import re

class AquaReaderScraper(MangaScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://aquareader.net"

    def is_supported(self, url):
        return "aquareader.net" in url

    def extract_manga_id_from_url(self, url):
        # https://aquareader.net/manga/solo-leveling
        if '/manga/' in url:
            parts = url.split('/manga/')
            if len(parts) > 1:
                return parts[-1].strip('/').split('?')[0]
        return None

    async def parse_url_to_manga(self, url):
        manga_id = self.extract_manga_id_from_url(url)
        if not manga_id:
            return None
        return await self.get_manga_details(manga_id)

    async def get_manga_details(self, manga_id):
        url = f"{self.base_url}/manga/{manga_id}"
        html = await self.fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        title_tag = soup.find('h1', class_='entry-title')
        if not title_tag:
            return None
        title = title_tag.text.strip()

        img_tag = soup.find('div', class_='summary_image').find('img') if soup.find('div', class_='summary_image') else None
        cover_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else ''

        synopsis_div = soup.find('div', class_='summary__content')
        synopsis = synopsis_div.text.strip() if synopsis_div else "No synopsis available."

        # Chapters
        chapters = []
        chap_list = soup.find('ul', class_='main.version-chap')
        if not chap_list:
            chap_list = soup.find('ul', class_='main version-chap')

        if chap_list:
            for item in chap_list.find_all('li', class_='wp-manga-chapter'):
                a_tag = item.find('a')
                if not a_tag:
                    continue
                chap_title = a_tag.text.strip()
                chap_url = a_tag['href']
                # extract chapter slug
                # https://aquareader.net/manga/solo-leveling/chapter-1/
                slug = chap_url.strip('/').split('/')[-1]
                if not slug:
                    continue

                # Determine chapter number for sorting
                num = 0.0
                try:
                    parts = chap_title.lower().replace('chapter', '').strip().split()
                    if parts:
                        num = float(parts[0].replace('-', '.'))
                except:
                    pass

                chapters.append({
                    "id": f"{manga_id}/{slug}",
                    "title": chap_title,
                    "url": chap_url,
                    "number": num
                })

        return {
            "id": manga_id,
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "chapters": chapters,
            "source": "aquareader"
        }

    async def get_chapter_images(self, chapter_url):
        html = await self.fetch_html(chapter_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        reading_content = soup.find('div', class_='reading-content')
        if not reading_content:
            return []

        images = []
        for img in reading_content.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                images.append(src.strip())

        return images
