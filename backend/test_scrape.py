import requests
from bs4 import BeautifulSoup

url = "https://aquareader.net/?s=solo+leveling&post_type=wp-manga"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

items = soup.select('.c-tabs-item__content')
for item in items[:2]:
    title_el = item.select_one('.post-title h3 a')
    if title_el:
        print("Title:", title_el.text.strip())
        print("Link:", title_el['href'])

import asyncio
from scrapers.mangadex import MangaDexScraper
from scrapers.aquareader import AquaReaderScraper

async def test_latest():
    md = MangaDexScraper()
    md_res = await md.get_latest_updates()
    print(f"MangaDex latest updates count: {len(md_res)}")
    if md_res:
        print("First:", md_res[0])
    await md.close()

    aq = AquaReaderScraper()
    aq_res = await aq.get_latest_updates()
    print(f"AquaReader latest updates count: {len(aq_res)}")
    await aq.close()

if __name__ == "__main__":
    asyncio.run(test_latest())

from tasks import fetch_global_latest_updates_job

def test_celery_task():
    print("Testing fetch_global_latest_updates_job locally...")
    fetch_global_latest_updates_job()
    print("Job completed successfully!")

if __name__ == "__main__":
    test_celery_task()
