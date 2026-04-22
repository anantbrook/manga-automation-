import aiohttp
import asyncio
from abc import ABC, abstractmethod
import logging

import os
import random

logger = logging.getLogger(__name__)

class MangaScraper(ABC):
    def __init__(self):
        self._session = None
        proxies_env = os.environ.get('PROXIES', '')
        self.proxies = [p.strip() for p in proxies_env.split(',')] if proxies_env else []

    async def get_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def get_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_with_retry(self, url, method="GET", retries=3, backoff_factor=2, **kwargs):
        """
        Helper method to perform HTTP requests with exponential backoff.
        Handles rate limits (429) and temporary server errors (502, 503, 504).
        """
        session = await self.get_session()
        for attempt in range(retries):
            proxy = self.get_proxy()
            if proxy:
                kwargs['proxy'] = proxy

            try:
                if method == "GET":
                    async with session.get(url, **kwargs) as response:
                        if response.status in (429, 502, 503, 504):
                            logger.warning("Attempt %d failed with status %d for %s", attempt + 1, response.status, url)
                            if attempt < retries - 1:
                                await asyncio.sleep(backoff_factor ** attempt)
                                continue
                        response.raise_for_status()
                        if 'json' in response.headers.get('Content-Type', ''):
                            return await response.json()
                        return await response.text()
                # If we need POST in the future
                elif method == "POST":
                    async with session.post(url, **kwargs) as response:
                        if response.status in (429, 502, 503, 504):
                            logger.warning("Attempt %d failed with status %d for %s", attempt + 1, response.status, url)
                            if attempt < retries - 1:
                                await asyncio.sleep(backoff_factor ** attempt)
                                continue
                        response.raise_for_status()
                        if 'json' in response.headers.get('Content-Type', ''):
                            return await response.json()
                        return await response.text()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Attempt %d failed with error %s for %s", attempt + 1, type(e).__name__, url)
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_factor ** attempt)
                    continue
                logger.error("All %d retries failed for %s", retries, url)
                raise
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
