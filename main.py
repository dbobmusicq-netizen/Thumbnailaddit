import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest, Conflict

# ---------------------------------------------------------------------------
# 🌐 KEEP ALIVE SERVER (Required for Render)
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Titan Bot is Online. 🚀"

def run_flask():
    # Render requires port 8080
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# ⚙️ CONFIGURATION
# ---------------------------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 STORAGE
# ---------------------------------------------------------------------------
users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"thumb_id": None}
    return users_db[user_id]

# ---------------------------------------------------------------------------
# 🛠️ HANDLERS
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Titan Bot Live**\n\n"
        "1. Send **Photo** (Thumbnail)\n"
        "2. Send **File/Video** (4GB+)\n\n"
        "ℹ️ *I send everything as Files to ensure thumbnails work.*"
    )

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file_id = update.message.photo[-1].file_id
    get_user(user_id)["thumb_id"] = file_id
    
    await update.message.reply_text("✅ Thumbnail Saved! Send your file now.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Check for thumbnail
    if not user_data.get("thumb_id"):
        await msg.reply_text("❌ Send a photo first!")
        return

    thumb_id = user_data["thumb_id"]
    caption = msg.caption or ""
    
    status = await msg.reply_text("⚡ Processing...")

    try:
        # 2. Identify File ID
        file_id_to_send = None
        if msg.video:
            file_id_to_send = msg.video.file_id
        elif msg.document:
            file_id_to_send = msg.document.file_id
            
        # 3. Send as Document (The Fix)
        if file_id_to_send:
            await msg.reply_document(
                document=file_id_to_send,
                thumbnail=thumb_id,   # ✅ FIXED: 'thumbnail', not 'thumb'
                caption=caption
            )
            
            # Clear thumbnail (Optional: remove this line if you want to keep thumb)
            user_data["thumb_id"] = None
            
            await status.delete()
        else:
            await status.edit_text("❌ Unknown file type.")

    except BadRequest as e:
        logger.error(f"Telegram Error: {e}")
        await status.edit_text(f"❌ Error: {e}")
    except Exception as e:
        logger.error(f"System Error: {e}")
        await status.edit_text("❌ Failed to process request.")

# ---------------------------------------------------------------------------
# 🚀 MAIN
# ---------------------------------------------------------------------------
def main():
    if not TOKEN:
        print("❌ BOT_TOKEN missing.")
        return

    start_keep_alive()
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    print("⚡ Titan Bot Started...")
    
    # drop_pending_updates ignores old messages piled up during crash
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
