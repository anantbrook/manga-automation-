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
        """Returns a list of recently updated manga (e.g. {'id', 'title', 'source'})"""
        pass
