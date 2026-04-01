import os
import sys
import subprocess
import time
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    print("Starting Flask Web Server...")
    # Run flask as a subprocess
    flask_process = subprocess.Popen([sys.executable, "app.py"])

    print("Starting Telegram Bot...")
    # Run bot as a subprocess
    bot_process = subprocess.Popen([sys.executable, "bot.py"])

    try:
        while True:
            time.sleep(1)
            # Check if either crashed
            if flask_process.poll() is not None:
                print("Flask server crashed! Shutting down...")
                break
            if bot_process.poll() is not None:
                print("Telegram bot crashed! Shutting down...")
                break
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        flask_process.terminate()
        bot_process.terminate()
        flask_process.wait()
        bot_process.wait()
        print("Goodbye.")
