import requests
from bs4 import BeautifulSoup
import asyncio

from scrapers.mangadex import MangaDexScraper
import aiohttp

async def test_mangadex():
    scraper = MangaDexScraper()
    res = await scraper.search_manga("solo leveling")
    print(res)
    session = await scraper.get_session()
    await session.close()

if __name__ == "__main__":
    asyncio.run(test_mangadex())
