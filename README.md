# 🔥 MangaFire PRO 🔥

A fully optimized, scalable, and monetization-ready Manga aggregator and reading platform.

## Features
- **Multi-Source Scraping**: Scrapes from AquaReader, Asura Scans, MangaDex, and Manganato.
- **Asynchronous Background Jobs**: Uses Celery + Redis to auto-download chapters and check for updates.
- **PostgreSQL Database**: Replaced SQLite with PostgreSQL for scalable production traffic.
- **React SPA Frontend**: Cyberpunk aesthetic with dark mode, infinite scroll manga cards, and a reader mode.
- **Monetization Built-in**: AdSense/PropellerAds placeholders and Affiliate Merch banners integrated into the UI.
- **Telegram Auto-Growth**: A fully functional Telegram bot that auto-shares new chapters to your channels.

## Requirements
- Python 3.10+
- Node.js & npm (for frontend building)
- Redis Server (for Celery queues)
- PostgreSQL (or fallback to SQLite via `DATABASE_URL`)

## One-Click Start

**Windows:**
Double-click `start_manga_fire.bat`

**Linux/Mac:**
```bash
./start_manga_fire.sh
```

## Environment Variables
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/mangafire
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
TELEGRAM_BOT_TOKEN=your_bot_token_here
AUTO_SHARE_CHANNELS=@your_manga_channel,-100123456789
PROXIES=http://proxy1.com:8080,http://proxy2.com:8080
ADMIN_TOKEN=your_secure_admin_token
```

## Admin Dashboard
Access the admin panel at `http://localhost:5000/admin/?token=your_secure_admin_token`.
From here, you can paste the URL of a manga (e.g., from Asura Scans), and the background workers will instantly start downloading it and its chapters.
