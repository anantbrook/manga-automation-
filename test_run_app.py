import os
import requests
import time
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
        # Run playwright script while server is up
        os.system("python /home/jules/verification/verify_cuj.py")
    finally:
        p.terminate()
        p.join()
