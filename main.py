import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest

# ---------------------------------------------------------------------------
# 🌐 KEEP ALIVE (Render Web Service Requirement)
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Titan Bot is Running efficiently. 🚀"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# ⚙️ CONFIGURATION
# ---------------------------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 MEMORY STORAGE
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
        "⚡ **Titan Bot (Fixed)**\n\n"
        "1. Send **Photo** (Sets Thumbnail)\n"
        "2. Send **Video/File** (4GB+ Supported)\n\n"
        "✅ *Thumbnail Mode: Force Document*",
        parse_mode="Markdown"
    )

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Store the file_id string only. Zero download.
    file_id = update.message.photo[-1].file_id
    get_user(user_id)["thumb_id"] = file_id
    
    await update.message.reply_text(
        "🖼️ **Thumbnail ID Saved!**\n"
        "Now send your Video or File.",
        quote=True
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Check if thumbnail exists
    if not user_data.get("thumb_id"):
        await msg.reply_text("❌ **No Thumbnail Set.** Please send a photo first.", quote=True)
        return

    thumb_id = user_data["thumb_id"]
    caption = msg.caption or ""

    # Status message (useful for large files to know bot accepted request)
    status = await msg.reply_text("⚡ **Processing...**")

    try:
        # 2. THE FIX: Use 'reply_document' + 'thumb' parameter
        # regardless of input type. This forces Telegram to render
        # our custom thumbnail instead of the original video preview.
        
        file_id_to_send = None
        
        if msg.video:
            file_id_to_send = msg.video.file_id
        elif msg.document:
            file_id_to_send = msg.document.file_id
            
        if file_id_to_send:
            await msg.reply_document(
                document=file_id_to_send,
                thumb=thumb_id,     # ✅ USING RAW API PARAMETER
                caption=caption
            )
            
        await status.delete()

    except BadRequest as e:
        logger.error(f"Telegram API Error: {e}")
        await status.edit_text(f"❌ **Telegram Error:** {e}")
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

    start_keep_alive()
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    print("⚡ Titan Bot is Online...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
