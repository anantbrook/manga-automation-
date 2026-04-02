from abc import ABC, abstractmethod

class MangaScraper(ABC):
    @abstractmethod
    async def search_manga(self, query: str) -> list:
        pass

    @abstractmethod
    async def get_manga_details(self, manga_id: str) -> dict:
        pass

    @abstractmethod
    async def get_chapter_images(self, manga_id: str, chapter_id: str) -> list:
        pass
