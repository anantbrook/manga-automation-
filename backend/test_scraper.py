import asyncio
from scrapers import get_scraper

async def test_mangadex():
    scraper = get_scraper('mangadex')
    details = await scraper.get_manga_details('32d76d19-8a05-4db0-9fc2-e0b0648fe9d0') # Solo leveling ID
    print("MangaDex Chapters:", len(details['chapters']) if details else 'Failed to fetch details')
    await scraper.close()

if __name__ == '__main__':
    asyncio.run(test_mangadex())
