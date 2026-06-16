import aiohttp
import asyncio
from abc import ABC, abstractmethod

import os
import random

class MangaScraper(ABC):
    def __init__(self):
        self._session = None
        proxies_env = os.environ.get('PROXIES', '')
        self.proxies = [p.strip() for p in proxies_env.split(',')] if proxies_env else []

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def get_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_with_retry(self, url, method="GET", headers=None, params=None, is_json=True, max_retries=4):
        session = await self.get_session()
        for attempt in range(max_retries):
            proxy = self.get_proxy()
            try:
                if method == "GET":
                    async with session.get(url, headers=headers, params=params, proxy=proxy, timeout=15) as response:
                        if response.status in [429, 502, 503]:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        response.raise_for_status()
                        if is_json:
                            return await response.json()
                        return await response.text()
                elif method == "POST":
                    # Assume POST is used for some internal APIs if needed, though we primarily GET
                    async with session.post(url, headers=headers, data=params, proxy=proxy, timeout=15) as response:
                        if response.status in [429, 502, 503]:
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

    @abstractmethod
    async def search_manga(self, query: str) -> list:
        pass

    @abstractmethod
    async def get_manga_details(self, manga_id: str) -> dict:
        pass

    @abstractmethod
    async def get_chapter_images(self, manga_id: str, chapter_id: str) -> list:
        pass

    @abstractmethod
    async def get_latest_updates(self) -> list:
        pass
