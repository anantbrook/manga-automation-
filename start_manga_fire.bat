@echo off
echo 🔥 Starting MangaFire PRO 🔥

echo Starting Redis server...
:: Assuming redis-server is in PATH for Windows users
start /b redis-server

echo Starting Celery Worker...
start /b celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo

echo Starting Celery Beat...
start /b celery -A app.core.celery_app.celery_app beat --loglevel=info

if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo ⚠️ TELEGRAM_BOT_TOKEN is not set. Bot will not run.
) else (
    echo Starting Telegram Bot...
    start /b python bot.py
)

echo Starting Flask Server on http://localhost:5000
set FLASK_APP=app:create_app
set FLASK_ENV=production
set FLASK_DEBUG=0
python run.py
