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

            flask_status = flask_process.poll()
            bot_status = bot_process.poll()

            # If both servers crashed, exit
            if flask_status is not None and bot_status is not None:
                print("Both servers have shut down.")
                break

            # If the web app crashes, it's usually fatal to the project
            if flask_status is not None:
                print("Flask server crashed! Shutting down bot as well...")
                break

            # If the bot crashes, we just warn the user, but leave the web app running
            if bot_status is not None:
                print("Warning: Telegram bot crashed! (Did you set the token?). The web server is still running.", flush=True)
                # We stop monitoring the bot but keep monitoring Flask
                flask_process.wait()
                break

    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        if flask_process.poll() is None:
            flask_process.terminate()
        if bot_process.poll() is None:
            bot_process.terminate()
        flask_process.wait()
        bot_process.wait()
        print("Goodbye.")
