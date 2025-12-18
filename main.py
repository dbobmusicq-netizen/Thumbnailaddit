import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest, TimedOut

# ---------------------------------------------------------------------------
# 🌐 KEEP ALIVE SERVER (Runs inside main.py)
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Titan Bot is Alive! 🚀"

def run_flask():
    # Run Flask on port 8080 (Render's default)
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# 🤖 BOT CONFIGURATION
# ---------------------------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 BOT LOGIC
# ---------------------------------------------------------------------------
users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"thumb": None}
    return users_db[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Titan Bot Online**\n\n1. Send Photo (Thumbnail)\n2. Send Video/File (Up to 4GB)",
        parse_mode="Markdown"
    )

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file_id = update.message.photo[-1].file_id
    get_user(user_id)["thumb"] = file_id
    await update.message.reply_text("✅ Thumbnail Saved! Now send the video.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    if not user_data["thumb"]:
        await msg.reply_text("❌ Send a photo thumbnail first!")
        return

    status = await msg.reply_text("⚡ Processing...")

    try:
        media_id = msg.video.file_id if msg.video else msg.document.file_id
        
        # Extended timeouts for 4GB files
        await context.bot.send_video(
            chat_id=msg.chat_id,
            video=media_id,
            thumbnail=user_data["thumb"],
            caption=msg.caption or "",
            supports_streaming=True,
            read_timeout=120, 
            write_timeout=120,
            connect_timeout=120
        )
        await status.delete()
    except Exception as e:
        await status.edit_text(f"Error: {e}")

# ---------------------------------------------------------------------------
# 🚀 MAIN ENTRY POINT
# ---------------------------------------------------------------------------
def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN is missing!")
        return

    # 1. Start Web Server first
    start_keep_alive()

    # 2. Start Bot
    print("⚡ Starting Titan Bot...")
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    # 3. Run safely
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
