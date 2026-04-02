import os
import requests
import time
from multiprocessing import Process
from app import create_app

app = create_app()

def run_server():
    os.environ["DATABASE_URL"] = "sqlite:///manga.db"
    app.run(port=5000)

if __name__ == '__main__':
    p = Process(target=run_server)
    p.start()
    time.sleep(3)

    try:
        r = requests.get("http://localhost:5000/api/health")
        print("Health Check:", r.json())
        assert r.status_code == 200

        r = requests.get("http://localhost:5000/")
        assert "MANGAFIRE PRO" in r.text or "<div id=\"root\"></div>" in r.text
        print("Frontend Serving OK")

    finally:
        p.terminate()
        p.join()
