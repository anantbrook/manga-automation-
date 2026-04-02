#!/bin/bash
echo "🔥 Starting MangaFire PRO 🔥"

# Ensure dependencies are installed
# pip install -r requirements.txt

# Start Redis (if not running)
if ! pgrep -x "redis-server" > /dev/null
then
    echo "Starting Redis server..."
    redis-server --daemonize yes
fi

# 1. Start Celery Worker
echo "Starting Celery Worker..."
celery -A app.core.celery_app.celery_app worker --loglevel=info > celery_worker.log 2>&1 &
CELERY_PID=$!

# 2. Start Celery Beat (for cron jobs)
echo "Starting Celery Beat..."
celery -A app.core.celery_app.celery_app beat --loglevel=info > celery_beat.log 2>&1 &
BEAT_PID=$!

# 3. Start Telegram Bot
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️ TELEGRAM_BOT_TOKEN is not set. Bot will not run."
else
    echo "Starting Telegram Bot..."
    python3 bot.py > bot.log 2>&1 &
    BOT_PID=$!
fi

# 4. Start Flask App
echo "Starting Flask Server on http://localhost:5000"
export FLASK_APP=app:create_app
export FLASK_ENV=production
export FLASK_DEBUG=0
python3 run.py

# Cleanup on exit
trap "kill $CELERY_PID $BEAT_PID $BOT_PID; exit" SIGINT SIGTERM
