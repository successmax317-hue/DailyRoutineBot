import os
import datetime
import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
# Ensure the data directory exists on your Railway Volume
DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)


def get_top_news() -> str:
    try:
        url = "https://api.rss2json.com/v1/api.json?rss_url=http://feeds.bbci.co.uk/news/rss.xml"
        res = requests.get(url, timeout=5).json()
        items = res.get("items", [])[:3]
        
        headlines = ["<b>📰 Top Headlines:</b>"]
        for idx, item in enumerate(items, 1):
            headlines.append(f"{idx}. <a href='{item['link']}'>{item['title']}</a>")
        return "\n".join(headlines)
    except Exception as e:
        logging.error(f"Failed to fetch news: {e}")
        return "<b>📰 Top Headlines:</b>\nUnable to load news right now."


def generate_briefing() -> str:
    today = datetime.datetime.now().strftime("%A, %B %d, %Y")
    news = get_top_news()
    return (
        f"<b>🌅 Good Morning!</b>\n"
        f"📅 <b>Date:</b> {today}\n\n"
        f"{news}\n\n"
        f"<b>📌 Today's Focus:</b>\n"
        f"• Check emails & set daily goals\n"
        f"• Stay hydrated!"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "<b>Welcome to your Personal Routine & Briefing Bot!</b>\n\n"
        "Commands:\n"
        "• /briefing - Get an instant briefing\n"
        "• /set_routine HH:MM - Set daily briefing time (e.g., <code>/set_routine 07:00</code>)\n"
        "• /unset_routine - Cancel daily briefing"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def send_instant_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = generate_briefing()
    await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


async def scheduled_briefing_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    text = generate_briefing()
    await context.bot.send_message(
        chat_id=job.chat_id, 
        text=text, 
        parse_mode="HTML", 
        disable_web_page_preview=True
    )


async def set_routine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    if not context.args:
        await update.message.reply_text("Usage: <code>/set_routine HH:MM</code>", parse_mode="HTML")
        return

    try:
        time_str = context.args[0]
        time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
        
        current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        for j in current_jobs:
            j.schedule_removal()

        context.job_queue.run_daily(
            scheduled_briefing_job,
            time=time_obj,
            chat_id=chat_id,
            name=str(chat_id)
        )

        await update.message.reply_text(
            f"✅ Daily briefing set for <b>{time_str}</b>.",
            parse_mode="HTML"
        )
    except ValueError:
        await update.message.reply_text("Invalid format! Use <code>HH:MM</code>.", parse_mode="HTML")


async def unset_routine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    
    if not jobs:
        await update.message.reply_text("No active routine set.")
        return

    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("🗑️ Daily briefing routine canceled.")


def main():
    # Setup persistent storage file
    persistence_file = os.path.join(DATA_DIR, "bot_persistence.pickle")
    persistence = PicklePersistence(filepath=persistence_file)

    # Attach persistence to application builder
    app = Application.builder().token(TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("briefing", send_instant_briefing))
    app.add_handler(CommandHandler("set_routine", set_routine))
    app.add_handler(CommandHandler("unset_routine", unset_routine))

    print("Bot is up and running with persistence...")
    app.run_polling()


if __name__ == "__main__":
    main()
