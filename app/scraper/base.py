import aiohttp
import asyncio
import os
import random
from bs4 import BeautifulSoup
from app.core.logger import logger

class MangaScraper:
    """Base class for all manga scrapers."""

    def __init__(self):
        self.proxies = self._load_proxies()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _load_proxies(self):
        proxies_env = os.getenv('PROXIES', '')
        if proxies_env:
            return [p.strip() for p in proxies_env.split(',') if p.strip()]
        return []

    def get_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    async def get_session(self):
        if not hasattr(self, '_session') or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            # Increase connection limits and reuse connections
            connector = aiohttp.TCPConnector(limit=50, keepalive_timeout=60)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session

    async def close_session(self):
        if hasattr(self, '_session') and not self._session.closed:
            await self._session.close()

    async def fetch_html(self, url, retries=3):
        proxy = self.get_proxy()
        session = await self.get_session()
        for attempt in range(retries):
            try:
                async with session.get(url, headers=self.headers, proxy=proxy) as response:
                    response.raise_for_status()
                    # Add small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    return await response.text()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url} via {proxy}: {e}")
                if attempt == retries - 1:
                    logger.error(f"All retries failed for {url}")
                    return None
                await asyncio.sleep(2 ** attempt) # Exponential backoff
        return None

    async def fetch_json(self, url, params=None, retries=3):
        proxy = self.get_proxy()
        session = await self.get_session()
        for attempt in range(retries):
            try:
                async with session.get(url, headers=self.headers, proxy=proxy, params=params) as response:
                    response.raise_for_status()
                    await asyncio.sleep(0.5)
                    return await response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url} via {proxy}: {e}")
                if attempt == retries - 1:
                    logger.error(f"All retries failed for JSON {url}")
                    return None
                await asyncio.sleep(2 ** attempt)
        return None

    async def download_image(self, url, filepath, referer=None, retries=3):
        headers = self.headers.copy()
        if referer:
            headers['Referer'] = referer

        proxy = self.get_proxy()
        session = await self.get_session()
        for attempt in range(retries):
            try:
                async with session.get(url, headers=headers, proxy=proxy) as response:
                    response.raise_for_status()
                    content = await response.read()
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    return True
            except Exception as e:
                logger.warning(f"Image download failed for {url}: {e}")
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(1)
        return False

    async def parse_url_to_manga(self, url):
        """Parse a direct URL and return a dict with basic manga details. Override in subclass."""
        raise NotImplementedError()

    async def get_manga_details(self, manga_id):
        """Fetch details like synopsis, cover, and chapter list. Override in subclass."""
        raise NotImplementedError()

    async def get_chapter_images(self, chapter_url):
        """Fetch a list of image URLs for a given chapter. Override in subclass."""
        raise NotImplementedError()
