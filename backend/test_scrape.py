import asyncio
from scrapers import get_scraper

async def test():
    scraper = get_scraper('mangadex')
    print("Testing MangaDex Scraper Search...")
    results = await scraper.search_manga("leveling")
    print("Search Results:", len(results))

    print("\nTesting MangaDex Latest Updates...")
    updates = await scraper.get_latest_updates()
    print("Updates Results:", len(updates))

    print("\nTesting AquaReader Scraper Search...")
    aqua = get_scraper('aquareader')
    res = await aqua.search_manga("solo leveling")
    print("Aqua Search Results:", len(res))

    await scraper.close()
    await aqua.close()

if __name__ == '__main__':
    asyncio.run(test())
