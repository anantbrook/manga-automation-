import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from sqlalchemy import or_

from app import create_app
from app.models import db
from app.models.manga import Manga
from app.models.chapter import Chapter
from app.models.subscription import Subscription

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AUTO_SHARE_CHANNELS = [c.strip() for c in os.getenv('AUTO_SHARE_CHANNELS', '').split(',') if c.strip()]

flask_app = create_app()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🔥 Welcome to MangaFire Pro Bot! 🔥\n\n"
        "Commands:\n"
        "/search <query> - Search for manga\n"
        "/manga <id> - Get details for a manga\n"
        "/latest - Get the latest updated manga\n"
        "/popular - Get popular manga\n"
        "/subscribe <id> - Get notified of new chapters\n"
        "/unsubscribe <id> - Stop notifications\n"
        "/subs - List your subscriptions\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_msg)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a query. Example: /search solo")
        return

    query = " ".join(context.args)
    with flask_app.app_context():
        mangas = Manga.query.filter(or_(Manga.title.ilike(f'%{query}%'), Manga.id.ilike(f'%{query}%'))).limit(5).all()

        if not mangas:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No results found in the database.")
            return

        response = "📚 **Search Results:**\n\n"
        for m in mangas:
            response += f"• *{m.title}*\n  ID: `{m.id}`\n\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with flask_app.app_context():
        mangas = Manga.query.order_by(Manga.last_updated.desc()).limit(5).all()
        if not mangas:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No manga available yet.")
            return

        response = "🔥 **Latest Updates:**\n\n"
        for m in mangas:
            response += f"• *{m.title}*\n  ID: `{m.id}`\n\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def popular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with flask_app.app_context():
        mangas = Manga.query.limit(5).all()
        if not mangas:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No manga available yet.")
            return

        response = "⭐ **Popular Manga:**\n\n"
        for m in mangas:
            response += f"• *{m.title}*\n  ID: `{m.id}`\n\n"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def manga_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Provide an ID. Example: /manga solo-leveling")
        return

    manga_id = context.args[0]

    with flask_app.app_context():
        manga = db.session.get(Manga, manga_id)
        if not manga:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Manga not found.")
            return

        chap_count = Chapter.query.filter_by(manga_id=manga.id).count()
        synopsis = manga.synopsis[:300] + "..." if manga.synopsis and len(manga.synopsis) > 300 else manga.synopsis

        response = (
            f"📖 *{manga.title}*\n\n"
            f"*{synopsis}*\n\n"
            f"Chapters: {chap_count}\n"
            f"Source: {manga.source}\n"
        )

        await context.bot.send_message(chat_id=update.effective_chat.id, text=response, parse_mode='Markdown')

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Provide an ID. Example: /subscribe solo-leveling")
        return

    manga_id = context.args[0]
    chat_id = str(update.effective_chat.id)

    with flask_app.app_context():
        manga = db.session.get(Manga, manga_id)
        if not manga:
            await context.bot.send_message(chat_id=chat_id, text="Manga not found in database.")
            return

        sub = Subscription.query.filter_by(chat_id=chat_id, manga_id=manga_id).first()
        if sub:
            await context.bot.send_message(chat_id=chat_id, text=f"You are already subscribed to {manga.title}.")
            return

        new_sub = Subscription(chat_id=chat_id, manga_id=manga_id)
        db.session.add(new_sub)
        db.session.commit()

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Subscribed to '{manga.title}'!")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Provide an ID.")
        return

    manga_id = context.args[0]
    chat_id = str(update.effective_chat.id)

    with flask_app.app_context():
        sub = Subscription.query.filter_by(chat_id=chat_id, manga_id=manga_id).first()
        if not sub:
            await context.bot.send_message(chat_id=chat_id, text="You are not subscribed.")
            return

        db.session.delete(sub)
        db.session.commit()

    await context.bot.send_message(chat_id=chat_id, text=f"❌ Unsubscribed from '{manga_id}'.")

async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    with flask_app.app_context():
        subs = Subscription.query.filter_by(chat_id=chat_id).all()
        if not subs:
            await context.bot.send_message(chat_id=chat_id, text="No subscriptions.")
            return

        response = "📋 **Your Subscriptions:**\n\n"
        for sub in subs:
            manga = db.session.get(Manga, sub.manga_id)
            title = manga.title if manga else sub.manga_id
            response += f"• {title} (`{sub.manga_id}`)\n"

    await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')

async def broadcast_new_chapter(bot, manga_title, manga_id, chapter_title, url_slug):
    msg = f"🔥 **New Chapter Alert!** 🔥\n\n*{manga_title}*\n{chapter_title}\n\nRead here: http://localhost:5000/manga/{manga_id}/{url_slug}"

    for channel in AUTO_SHARE_CHANNELS:
        try:
            await bot.send_message(chat_id=channel, text=msg, parse_mode='Markdown')
        except Exception as e:
            print(f"Failed to post to channel {channel}: {e}")

    with flask_app.app_context():
        subs = Subscription.query.filter_by(manga_id=manga_id).all()
        for sub in subs:
            try:
                await bot.send_message(chat_id=sub.chat_id, text=msg, parse_mode='Markdown')
            except:
                pass

def run_bot_instance():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set.")
        return None

    tg_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("search", search))
    tg_app.add_handler(CommandHandler("manga", manga_details))
    tg_app.add_handler(CommandHandler("latest", latest))
    tg_app.add_handler(CommandHandler("popular", popular))
    tg_app.add_handler(CommandHandler("subscribe", subscribe))
    tg_app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    tg_app.add_handler(CommandHandler("subs", list_subs))
    return tg_app

if __name__ == '__main__':
    bot_app = run_bot_instance()
    if bot_app:
        print("Starting Telegram Bot Polling...")
        bot_app.run_polling()
