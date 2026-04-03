import os
import time
import requests
from multiprocessing import Process
from app import create_app

app = create_app()

def run_server():
    os.environ["DATABASE_URL"] = "sqlite:///manga.db"
    app.run(port=5000, use_reloader=False)

if __name__ == '__main__':
    p = Process(target=run_server)
    p.start()
    time.sleep(3)

    try:
        # Test 1: Health
        r = requests.get("http://127.0.0.1:5000/api/health")
        print("Health Check:", r.status_code, r.json())

        # Test 2: Popular endpoint
        r = requests.get("http://127.0.0.1:5000/api/manga/popular")
        print("Popular Check:", r.status_code, r.json())

        # Test 3: Sitemap
        r = requests.get("http://127.0.0.1:5000/sitemap.xml")
        print("Sitemap Check:", r.status_code, r.text[:100])

        # Test 4: Frontend
        r = requests.get("http://127.0.0.1:5000/")
        print("Frontend Check:", r.status_code)

    finally:
        p.terminate()
        p.join()
