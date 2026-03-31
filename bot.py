import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from scraper import search_manga, get_manga_details

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🔥 Welcome to Manga-FireA Bot! 🔥\n\n"
        "Commands:\n"
        "/search <query> - Search for manga\n"
        "/manga <id> - Get details for a manga\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_msg)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a search query. Example: /search solo leveling")
        return

    query = " ".join(context.args)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🔍 Searching for '{query}'...")

    results = search_manga(query)
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

    details = get_manga_details(manga_id)
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

def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set. Telegram bot will not start.")
        return

    print("Starting Telegram Bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("manga", manga))

    app.run_polling()

if __name__ == '__main__':
    run_bot()
