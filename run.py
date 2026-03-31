import threading
import os
from dotenv import load_dotenv

load_dotenv()

# We need to run the bot in a separate thread/process if we want both in one go
def run_flask():
    from app import app
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

def run_telegram():
    import bot
    bot.run_bot()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_telegram)

    flask_thread.start()
    bot_thread.start()

    flask_thread.join()
    bot_thread.join()
