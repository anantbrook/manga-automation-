#!/bin/bash
echo "=============================================="
echo "🔥 Starting Manga-FireA Server & Telegram Bot 🔥"
echo "=============================================="

echo "[1/3] Checking dependencies..."
python3 -m pip install -r requirements.txt

echo "[2/3] Checking environment variables..."
if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    echo "TELEGRAM_BOT_TOKEN=YOUR_TOKEN_HERE" > .env
    echo "ADMIN_TOKEN=admin123" >> .env
    echo "Please edit the .env file with your actual Telegram bot token."
fi

echo "[3/3] Launching servers..."
echo "The website will be available at http://localhost:5000"
echo "Press CTRL+C to stop both servers."
echo "----------------------------------------------"

python3 run.py