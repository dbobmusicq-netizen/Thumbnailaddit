import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest, TimedOut

# ---------------------------------------------------------------------------
# 🌐 KEEP ALIVE SERVER
# ---------------------------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Titan Bot is Alive! 🚀"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ---------------------------------------------------------------------------
# 🤖 BOT CONFIGURATION
# ---------------------------------------------------------------------------
TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 MEMORY STORAGE
# ---------------------------------------------------------------------------
users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        # We store 'thumb_id' to download it later
        users_db[user_id] = {"thumb_id": None}
    return users_db[user_id]

# ---------------------------------------------------------------------------
# 🛠️ HANDLERS
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **Titan Thumbnail Bot Fixed**\n\n"
        "1. Send a **Photo** (Your Thumbnail)\n"
        "2. Send a **Video** or **File** (Up to 4GB)\n"
        "3. I will attach the thumb properly!",
        parse_mode="Markdown"
    )

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Get the file_id of the largest photo
    file_id = update.message.photo[-1].file_id
    get_user(user_id)["thumb_id"] = file_id
    
    await update.message.reply_text("✅ **Thumbnail Set!**\nNow send your Video or File.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Check if user has a thumbnail
    if not user_data.get("thumb_id"):
        await msg.reply_text("❌ **No Thumbnail!**\nPlease send a photo first.")
        return

    status = await msg.reply_text("⚡ **Downloading thumbnail & Processing...**")

    try:
        # 2. CRITICAL FIX: Download the Thumbnail Image to Memory
        # We cannot pass a file_id for a thumbnail. We must pass the BYTES.
        thumb_file = await context.bot.get_file(user_data["thumb_id"])
        thumb_data = await thumb_file.download_as_bytearray()

        # 3. Determine Media Type & ID
        media_id = msg.video.file_id if msg.video else msg.document.file_id
        caption = msg.caption or ""

        # 4. Send using the uploaded thumbnail bytes
        if msg.video:
            await context.bot.send_video(
                chat_id=msg.chat_id,
                video=media_id,
                thumbnail=thumb_data,  # Pass bytes, not ID
                caption=caption,
                supports_streaming=True,
                read_timeout=120,
                write_timeout=120
            )
        else:
            await context.bot.send_document(
                chat_id=msg.chat_id,
                document=media_id,
                thumbnail=thumb_data, # Pass bytes, not ID
                caption=caption,
                read_timeout=120,
                write_timeout=120
            )

        await status.delete()

    except BadRequest as e:
        await status.edit_text(f"❌ **Telegram Error:** {e}\n\n*Note: Telegram sometimes refuses to change thumbnails for existing files unless sent as a Document.*")
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit_text("❌ Failed to process.")

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

    print("⚡ Titan Bot Started...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
