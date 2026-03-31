import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://aquareader.net/"
}

BASE_URL = "https://aquareader.net"

def search_manga(query):
    url = f"{BASE_URL}/?s={query}&post_type=wp-manga"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []

        items = soup.select('.c-tabs-item__content')
        for item in items:
            title_el = item.select_one('.post-title h3 a')
            if not title_el:
                continue
            title = title_el.text.strip()
            link = title_el['href']

            # Extract ID or slug
            slug = link.strip('/').split('/')[-1]

            img_el = item.select_one('img')
            cover_url = img_el['src'] if img_el else None

            # Sometimes data-src is used for lazy loading
            if img_el and img_el.has_attr('data-src'):
                cover_url = img_el['data-src']
            elif img_el and img_el.has_attr('srcset'):
                # Quick parse of srcset to get the highest res image usually at the end or just take the src
                pass

            results.append({
                'id': slug,
                'title': title,
                'url': link,
                'cover_url': cover_url
            })
        return results
    except Exception as e:
        print(f"Error searching manga: {e}")
        return []

def get_manga_details(manga_id):
    url = f"{BASE_URL}/manga/{manga_id}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        title_el = soup.select_one('.post-title h1')
        title = title_el.text.strip() if title_el else manga_id

        # Remove "HOT" or other badges from title if present
        if title_el and title_el.select_one('span'):
            title = title.replace(title_el.select_one('span').text, '').strip()

        img_el = soup.select_one('.summary_image img')
        cover_url = img_el['data-src'] if img_el and img_el.has_attr('data-src') else (img_el['src'] if img_el else None)

        synopsis_el = soup.select_one('.summary__content')
        synopsis = synopsis_el.text.strip() if synopsis_el else "No synopsis available."

        # Need to fetch chapters. AquaReader uses an ajax call or a direct list
        # Usually it's in a list
        chapter_items = soup.select('.wp-manga-chapter')
        chapters = []

        # If chapters aren't loaded in the DOM directly, we might need to hit an admin-ajax endpoint.
        # Let's check if they are in the DOM first.
        if chapter_items:
            for item in chapter_items:
                a_tag = item.select_one('a')
                if a_tag:
                    chap_title = a_tag.text.strip()
                    chap_link = a_tag['href']
                    chap_slug = chap_link.strip('/').split('/')[-1]
                    chapters.append({
                        'id': f"{manga_id}/{chap_slug}",
                        'title': chap_title,
                        'url': chap_link
                    })
        else:
            # Try ajax
            manga_id_input = soup.select_one('#manga-chapters-holder')
            if manga_id_input and manga_id_input.has_attr('data-id'):
                internal_id = manga_id_input['data-id']
                ajax_url = f"{BASE_URL}/wp-admin/admin-ajax.php"
                data = {
                    'action': 'manga_get_chapters',
                    'manga': internal_id
                }
                ajax_r = requests.post(ajax_url, headers=HEADERS, data=data, timeout=10)
                if ajax_r.status_code == 200:
                    ajax_soup = BeautifulSoup(ajax_r.text, 'html.parser')
                    chapter_items = ajax_soup.select('.wp-manga-chapter')
                    for item in chapter_items:
                        a_tag = item.select_one('a')
                        if a_tag:
                            chap_title = a_tag.text.strip()
                            chap_link = a_tag['href']
                            chap_slug = chap_link.strip('/').split('/')[-1]
                            chapters.append({
                                'id': f"{manga_id}/{chap_slug}",
                                'title': chap_title,
                                'url': chap_link
                            })

        return {
            'id': manga_id,
            'title': title,
            'cover_url': cover_url,
            'synopsis': synopsis,
            'chapters': chapters
        }

    except Exception as e:
        print(f"Error fetching manga details: {e}")
        return None

def get_chapter_images(manga_id, chapter_id):
    url = f"{BASE_URL}/manga/{manga_id}/{chapter_id}/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        images = []
        img_blocks = soup.select('.page-break img')

        for idx, img in enumerate(img_blocks):
            img_url = img.get('data-src') or img.get('src')
            if img_url:
                images.append(img_url.strip())

        return images
    except Exception as e:
        print(f"Error fetching chapter images: {e}")
        return []

if __name__ == "__main__":
    print("Testing search...")
    res = search_manga("solo")
    print(res[:2])
    if res:
        manga_id = res[0]['id']
        print(f"\nTesting details for {manga_id}...")
        details = get_manga_details(manga_id)
        if details:
            print(f"Title: {details['title']}")
            print(f"Chapters found: {len(details['chapters'])}")
            if details['chapters']:
                chap_slug = details['chapters'][-1]['id'].split('/')[-1] # take first (usually latest or oldest)
                print(f"\nTesting images for {manga_id}/{chap_slug}...")
                imgs = get_chapter_images(manga_id, chap_slug)
                print(f"Images found: {len(imgs)}")
                print(f"First image: {imgs[0] if imgs else 'None'}")
