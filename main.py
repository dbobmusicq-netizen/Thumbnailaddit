import os
import logging
import asyncio
from datetime import datetime
from keep_alive import keep_alive  # Import the Keep Alive function
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    Defaults
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, TimedOut

# ---------------------------------------------------------------------------
# ⚙️ CONFIGURATION
# ---------------------------------------------------------------------------

# On Render, set 'BOT_TOKEN' in the "Environment Variables" section.
TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_IDS = [123456789] # REPLACE WITH YOUR INTEGER ID

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 MEMORY STORAGE
# ---------------------------------------------------------------------------
users_db = {}
bot_stats = {"processed": 0, "start": datetime.now()}

# ---------------------------------------------------------------------------
# 🛠️ CORE FUNCTIONS
# ---------------------------------------------------------------------------

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"thumb": None, "banned": False}
    return users_db[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"⚡ **Titan Bot Online**\n\n"
        f"Hi {user.first_name}! I add thumbnails to large files.\n\n"
        f"**Capabilities:**\n"
        f"✅ 1MB to 4GB+ Support\n"
        f"✅ Video & Documents\n"
        f"✅ Zero Quality Loss\n\n"
        f"**How to use:**\n"
        f"1. Send a Photo (Thumbnail)\n"
        f"2. Send a Video/File"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Get the largest available photo size
    file_id = update.message.photo[-1].file_id
    get_user(user_id)["thumb"] = file_id
    
    await update.message.reply_text(
        "🖼️ **Thumbnail Saved!**\n\nNow send your **4GB Video** or File.",
        quote=True
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles files from 1MB to 4GB using file_id reference.
    """
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Validation
    if not user_data["thumb"]:
        await msg.reply_text("❌ **Send a photo first!** I need a thumbnail.", quote=True)
        return

    # 2. Detect Type & ID
    media_id = None
    file_name = "Video"
    
    if msg.video:
        media_id = msg.video.file_id
        file_name = msg.video.file_name or "Video"
    elif msg.document:
        # Check mime type to ensure it's video-like if possible, or just allow all
        media_id = msg.document.file_id
        file_name = msg.document.file_name or "File"
    else:
        return

    # 3. Status Update
    status = await msg.reply_text(f"⚡ **Processing {file_name}...**")

    try:
        # 4. The 4GB Logic
        # We assume the file_id is valid on Telegram servers.
        # We send it back with the cached thumbnail ID.
        
        caption = msg.caption or f"📁 **{file_name}**"

        if msg.video:
            await context.bot.send_video(
                chat_id=msg.chat_id,
                video=media_id,
                thumbnail=user_data["thumb"],
                caption=caption,
                supports_streaming=True,
                read_timeout=60,    # Extended timeout for 4GB handshake
                write_timeout=60,
                connect_timeout=60
            )
        else:
            await context.bot.send_document(
                chat_id=msg.chat_id,
                document=media_id,
                thumbnail=user_data["thumb"],
                caption=caption,
                read_timeout=60,
                write_timeout=60
            )

        bot_stats["processed"] += 1
        await status.delete()

    except TimedOut:
        await status.edit_text("⚠️ **Telegram is slow.** The file is huge, but it should appear momentarily.")
    except BadRequest as e:
        await status.edit_text(f"❌ **Error:** {e}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit_text("❌ Failed to process.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    await update.message.reply_text(
        f"📊 **Stats:**\nProcessed: {bot_stats['processed']}\nUsers: {len(users_db)}"
    )

# ---------------------------------------------------------------------------
# 🚀 MAIN EXECUTION
# ---------------------------------------------------------------------------

def main():
    if not TOKEN:
        print("❌ CRITICAL: BOT_TOKEN is missing.")
        return

    # Start the fake server for Render
    keep_alive()

    # Build Bot with extended timeouts
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    print("⚡ Titan Bot is Running on Render...")
    app.run_polling()

if __name__ == '__main__':
    main()
