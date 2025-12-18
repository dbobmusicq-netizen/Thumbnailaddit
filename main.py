import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest

# ---------------------------------------------------------------------------
# 🌐 KEEP ALIVE (Required for Render Free Tier Port Binding)
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Titan Bot is Running efficiently. 🚀"

def run_flask():
    # Render expects a web server on port 8080
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# ⚙️ CONFIGURATION
# ---------------------------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 MEMORY STORAGE (RAM)
# ---------------------------------------------------------------------------
users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"thumb_id": None}
    return users_db[user_id]

# ---------------------------------------------------------------------------
# 🛠️ BOT LOGIC
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Titan Bot (Method-1)**\n\n"
        "1. Send **Photo** (Sets Thumbnail)\n"
        "2. Send **Video/File** (Bot attaches thumb by ID)\n\n"
        "🚀 *Zero-Download Mode Active*",
        parse_mode="Markdown"
    )

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # We grab the file_id of the photo.
    # We do NOT download it. We just store the ID string.
    file_id = update.message.photo[-1].file_id
    get_user(user_id)["thumb_id"] = file_id
    
    await update.message.reply_text(
        "🖼️ **Thumbnail ID Stored!**\n"
        "Now send your 4GB Video/Document.",
        quote=True
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The 'Senior Engineer' approach:
    Reuse file_id for Video AND Reuse file_id for Thumbnail.
    """
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Validation
    if not user_data.get("thumb_id"):
        await msg.reply_text("❌ **No Thumbnail Set.** Send a photo first!", quote=True)
        return

    # 2. Preparation
    thumb_id = user_data["thumb_id"]
    caption = msg.caption or "" # Keep original caption

    # Status (Optional, can be removed for speed)
    status = await msg.reply_text("⚡ **Titanium Plating...**")

    try:
        # 3. Execution (The Clean Way)
        if msg.video:
            await msg.reply_video(
                video=msg.video.file_id,
                thumbnail=thumb_id,  # PTB v20 uses 'thumbnail', sends to API as 'thumb'
                caption=caption,
                supports_streaming=True
            )
        elif msg.document:
            await msg.reply_document(
                document=msg.document.file_id,
                thumbnail=thumb_id,
                caption=caption
            )
        
        # Cleanup
        await status.delete()

    except BadRequest as e:
        logger.error(f"Telegram API Error: {e}")
        await status.edit_text(
            f"❌ **Telegram Error:** `{e}`\n\n"
            "This usually happens if the thumbnail format is invalid or Telegram rejected the ID map."
        )
    except Exception as e:
        logger.error(f"General Error: {e}")
        await status.edit_text("❌ System Error.")

# ---------------------------------------------------------------------------
# 🚀 MAIN
# ---------------------------------------------------------------------------
def main():
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN is missing!")
        return

    # Start Flask so Render doesn't kill the bot
    start_keep_alive()
    
    # Init Bot
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    print("⚡ Titan Bot is Online (High Performance Mode)...")
    
    # Drop pending updates to prevent startup flood
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
