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
