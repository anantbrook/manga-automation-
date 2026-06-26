import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import time
from scrapers import get_scraper
from models import db, Manga, Subscription, Chapter
from flask import Flask

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Create a minimal app context for the bot to interact with the database
app = Flask(__name__)
# Read the same DATABASE_URL as app.py (Postgres via Docker, or sqlite locally)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///manga.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🔥 Welcome to Manga-FireA Bot! 🔥\n\n"
        "Commands:\n"
        "/search <query> - Search for manga\n"
        "/manga <id> - Get details for a manga\n"
        "/subscribe <id> - Get notified of new chapters\n"
        "/unsubscribe <id> - Stop notifications\n"
        "/subs - List your subscriptions\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_msg)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a manga ID. Example: /subscribe solo-leveling")
        return

    manga_id = context.args[0]
    chat_id = str(update.effective_chat.id)

    with app.app_context():
        # Make sure manga exists in DB or fetch it
        manga = db.session.get(Manga, manga_id)
        if not manga:
            scraper = get_scraper('mangadex')
            # The bot is already running in an asyncio event loop, so we can just await
            details = await scraper.get_manga_details(manga_id)
            if not details:
                await context.bot.send_message(chat_id=chat_id, text="Manga not found.")
                return
            manga = Manga(id=details['id'], title=details['title'], cover_url=details['cover_url'])
            db.session.add(manga)

            # Add chapters so we know the baseline
            for chap in details['chapters']:
                chapter = Chapter(id=chap['id'], manga_id=manga_id, title=chap['title'], url=chap['url'])
                db.session.add(chapter)

            db.session.commit()

        # Check if already subscribed
        sub = Subscription.query.filter_by(chat_id=chat_id, manga_id=manga_id).first()
        if sub:
            await context.bot.send_message(chat_id=chat_id, text=f"You are already subscribed to {manga.title}.")
            return

        new_sub = Subscription(chat_id=chat_id, manga_id=manga_id)
        db.session.add(new_sub)
        db.session.commit()

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Successfully subscribed to updates for '{manga.title}'!")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a manga ID. Example: /unsubscribe solo-leveling")
        return

    manga_id = context.args[0]
    chat_id = str(update.effective_chat.id)

    with app.app_context():
        sub = Subscription.query.filter_by(chat_id=chat_id, manga_id=manga_id).first()
        if not sub:
            await context.bot.send_message(chat_id=chat_id, text="You are not subscribed to this manga.")
            return

        db.session.delete(sub)
        db.session.commit()

    await context.bot.send_message(chat_id=chat_id, text=f"❌ Unsubscribed from '{manga_id}'.")

async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    with app.app_context():
        subs = Subscription.query.filter_by(chat_id=chat_id).all()
        if not subs:
            await context.bot.send_message(chat_id=chat_id, text="You don't have any subscriptions.")
            return

        response = "📋 **Your Subscriptions:**\n\n"
        for sub in subs:
            manga = db.session.get(Manga, sub.manga_id)
            title = manga.title if manga else sub.manga_id
            response += f"• {title} (`{sub.manga_id}`)\n"

    await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a search query. Example: /search solo leveling")
        return

    query = " ".join(context.args)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔍 Searching for '{query}'...")

    scraper = get_scraper('mangadex')
    results = await scraper.search_manga(query)
    if not results:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No results found.")
        return

    response = "📚 **Search Results:**\n\n"
    for r in results[:5]: # Send top 5
        response += f"• *{r['title']}*\n  ID: `{r['id']}`\n\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def manga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a manga ID. Example: /manga solo-leveling")
        return

    manga_id = context.args[0]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"📥 Fetching details for '{manga_id}'...")

    scraper = get_scraper('mangadex')
    details = await scraper.get_manga_details(manga_id)
    if not details:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Manga not found or error fetching details.")
        return

    chap_count = len(details['chapters'])
    synopsis = details['synopsis'][:300] + "..." if len(details['synopsis']) > 300 else details['synopsis']

    response = (
        f"📖 *{details['title']}*\n\n"
        f"*{synopsis}*\n\n"
        f"Chapters: {chap_count}\n"
    )

    if details['cover_url']:
        try:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=details['cover_url'], caption=response, parse_mode='Markdown')
        except:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def popular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🔥 Fetching popular manga...")

    with app.app_context():
        trending = Manga.query.order_by(Manga.view_count.desc()).limit(5).all()

    if not trending:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No popular results found right now.")
        return

    response = "🌟 **Trending Now:**\n\n"
    for m in trending:
        response += f"• *{m.title}*\n  ID: `{m.id}`\n  Views: {m.view_count or 0}\n\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🆕 Check out the latest chapter releases directly on our website:\n\n🌐 https://your-mangafire-domain.com"
    )

async def check_updates_job(context: ContextTypes.DEFAULT_TYPE):
    """Background task to check for new chapters."""
    bot = context.bot
    try:
        with app.app_context():
            # Get all unique subscribed manga IDs
            subs = Subscription.query.all()
            unique_manga_ids = list(set([sub.manga_id for sub in subs]))

            scraper = get_scraper('mangadex')

            for manga_id in unique_manga_ids:
                manga_obj = db.session.get(Manga, manga_id)
                details = await scraper.get_manga_details(manga_id)

                # Sleep to respect rate limit without blocking loop
                await asyncio.sleep(2)

                if not details:
                    continue

                # Find new chapters
                new_chapters = []
                for chap in details['chapters']:
                    existing = db.session.get(Chapter, chap['id'])
                    if not existing:
                        chapter = Chapter(id=chap['id'], manga_id=manga_id, title=chap['title'], url=chap['url'])
                        db.session.add(chapter)
                        new_chapters.append(chap)

                if new_chapters:
                    db.session.commit()
                    # Notify subscribers
                    manga_subs = Subscription.query.filter_by(manga_id=manga_id).all()
                    for sub in manga_subs:
                        msg = f"🔥 **New Chapter Alert!** 🔥\n\n*{manga_obj.title}*\n\n"
                        for nc in new_chapters:
                            msg += f"• {nc['title']}\n"
                        try:
                            await bot.send_message(chat_id=sub.chat_id, text=msg, parse_mode='Markdown')
                        except Exception as e:
                            print(f"Failed to send update to {sub.chat_id}: {e}")

    except Exception as e:
        print(f"Error in update job: {e}")

def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return

    print("Starting Telegram Bot...")
    tg_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("search", search))
    tg_app.add_handler(CommandHandler("manga", manga))
    tg_app.add_handler(CommandHandler("subscribe", subscribe))
    tg_app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    tg_app.add_handler(CommandHandler("subs", list_subs))
    tg_app.add_handler(CommandHandler("popular", popular))
    tg_app.add_handler(CommandHandler("latest", latest))

    # Start the background update checker using JobQueue
    if tg_app.job_queue:
        tg_app.job_queue.run_repeating(check_updates_job, interval=3600, first=10) # Run every hour, starting in 10s

    tg_app.run_polling()

if __name__ == '__main__':
    run_bot()
