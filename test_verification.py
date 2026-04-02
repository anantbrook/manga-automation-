import asyncio

async def test_base_scraper_async():
    from app.scraper.base import MangaScraper
    scraper = MangaScraper()
    session = await scraper.get_session()
    assert not session.closed
    await scraper.close_session()
    assert session.closed

if __name__ == '__main__':
    asyncio.run(test_base_scraper_async())
    print("Scraper session verification passed.")
