import os
import time
import requests
from multiprocessing import Process

def run_server():
    os.environ['DATABASE_URL'] = 'sqlite:///manga.db'
    os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'True'  # Force celery to run locally without redis for the test
    from app import create_app
    app = create_app()
    app.run(port=5000, use_reloader=False)

if __name__ == '__main__':
    p = Process(target=run_server)
    p.start()
    time.sleep(5)

    try:
        r = requests.get('http://127.0.0.1:5000/api/manga/popular')
        print('Popular Check:', r.status_code, r.json())

        print("Triggering add manga via admin...")
        res = requests.post('http://127.0.0.1:5000/admin/?token=admin123', data={'url': 'https://aquareader.net/manga/solo-leveling'}, allow_redirects=True)
        print("Admin add status:", res.status_code)

        time.sleep(2)

        r = requests.get('http://127.0.0.1:5000/api/manga/popular')
        print('Popular Check after add:', r.status_code)
        print("Manga items:", len(r.json()))
        if len(r.json()) > 0:
            print("Successfully scraped manga title:", r.json()[0]['title'])

    finally:
        p.terminate()
        p.join()
