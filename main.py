import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest

# ---------------------------------------------------------------------------
# 🌐 KEEP ALIVE SERVER (For Render Free Tier)
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Titan Bot is Online & Healthy. 🚀"

def run_flask():
    # Render requires a web server listening on port 8080
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# ⚙️ CONFIGURATION
# ---------------------------------------------------------------------------
# Get token from Environment Variable
TOKEN = os.getenv("BOT_TOKEN")

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 IN-MEMORY STORAGE
# ---------------------------------------------------------------------------
users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"thumb_id": None}
    return users_db[user_id]

# ---------------------------------------------------------------------------
# 🛠️ BOT HANDLERS
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the welcome message."""
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"⚡ Titan Bot Ready\n\n"
        f"Hi {user}! I attach custom thumbnails to large files.\n\n"
        f"1. Send a Photo (This becomes the thumbnail)\n"
        f"2. Send a Video or File (Up to 4GB)\n\n"
        f"⚠️ Note: I force files as 'Documents' to ensure the thumbnail works."
    )

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the file_id of the sent photo."""
    user_id = update.effective_user.id
    
    # Telegram sends multiple sizes. The last one is the highest quality.
    # We store the file_id ONLY. We do not download the image.
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    get_user(user_id)["thumb_id"] = file_id
    
    await update.message.reply_text(
        "✅ Thumbnail Saved!\n"
        "Now send your Video or Document."
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    The Core Logic:
    1. Checks for stored thumbnail ID.
    2. Takes incoming file_id (Video/Doc).
    3. Re-sends as Document + thumb (Forces Telegram to render thumb).
    """
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Validation: Do we have a thumbnail?
    thumb_id = user_data.get("thumb_id")
    if not thumb_id:
        await msg.reply_text("❌ Please send a photo thumbnail first.")
        return

    # 2. Preparation
    caption = msg.caption or ""
    status = await msg.reply_text("⚡ Processing...")

    try:
        # Determine the file_id to reuse
        file_id_to_send = None
        if msg.video:
            file_id_to_send = msg.video.file_id
        elif msg.document:
            file_id_to_send = msg.document.file_id
        
        # 3. Execution: Force Document Strategy
        if file_id_to_send:
            await msg.reply_document(
                document=file_id_to_send,
                thumb=thumb_id,     # ✅ Uses raw 'thumb' param for ID reuse
                caption=caption
            )
            
            # 4. Cleanup: Clear thumb to prevent accidental reuse
            user_data["thumb_id"] = None
            
            await status.delete()
        else:
            await status.edit_text("❌ Unsupported file type.")

    except BadRequest as e:
        logger.error(f"Telegram Error: {e}")
        await status.edit_text(f"❌ Telegram Error: {e}")
        
    except Exception as e:
        logger.error(f"General Error: {e}")
        await status.edit_text("❌ System Error.")

# ---------------------------------------------------------------------------
# 🚀 MAIN EXECUTION
# ---------------------------------------------------------------------------
def main():
    if not TOKEN:
        print("❌ CRITICAL ERROR: 'BOT_TOKEN' environment variable is missing.")
        return

    # 1. Start Web Server (for Render)
    start_keep_alive()
    
    # 2. Initialize Bot
    application = ApplicationBuilder().token(TOKEN).build()
    
    # 3. Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    print("⚡ Titan Bot is Online (Production Mode)...")
    
    # 4. Run Polling
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
