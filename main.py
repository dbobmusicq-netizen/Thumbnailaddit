import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import BadRequest, Forbidden

# ---------------------------------------------------------------------------
# ⚙️ CONFIGURATION & SETUP
# ---------------------------------------------------------------------------

# Load Token from Env or Replace directly here
# For free hosting (Render/Railway), set these as Environment Variables.
TOKEN = os.getenv("BOT_TOKEN", "8391467781:AAGiwYCtIhw4yNYosQg_SjG8pDiubjIqghk")

# Add your Telegram User ID here for Admin access
ADMIN_IDS = [1745041582, 987654321]  # Replace with actual integer IDs

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 🧠 IN-MEMORY STORAGE (No Database - High Performance)
# ---------------------------------------------------------------------------

# Structure: {user_id: {"thumb_id": str, "joined_at": str, "banned": bool, "caption_mode": bool}}
users_db = {}

# Global Stats
bot_stats = {
    "files_processed": 0,
    "start_time": datetime.now()
}

# Maintenance Switch
maintenance_mode = False

# ---------------------------------------------------------------------------
# 🛠️ HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def get_user(user_id):
    """Ensure user exists in memory."""
    if user_id not in users_db:
        users_db[user_id] = {
            "thumb_id": None,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "banned": False,
            "caption_mode": True
        }
    return users_db[user_id]

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def restricted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check maintenance mode."""
    if maintenance_mode and not is_admin(update.effective_user.id):
        await update.message.reply_text("🚧 **Titan is currently under maintenance.**\nPlease try again later.")
        return True
    return False

# ---------------------------------------------------------------------------
# 🌈 USER HANDLERS (UX & LOGIC)
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await restricted(update, context): return
    
    user = update.effective_user
    get_user(user.id)
    
    text = (
        f"⚡ **Titan Thumbnail Bot** ⚡\n\n"
        f"Hey {user.first_name}! I am the **Principal Thumbnail Architect**.\n"
        f"I can add custom thumbnails to videos/files up to **4GB** instantly.\n\n"
        f"**🚀 How to use:**\n"
        f"1️⃣ Send me a Photo (This becomes your thumbnail)\n"
        f"2️⃣ Send me a Video or File\n"
        f"3️⃣ I will attach the thumbnail instantly!\n\n"
        f"✅ **No Quality Loss** | ✅ **4GB Support** | ✅ **Unlimited**"
    )
    
    keyboard = [
        [InlineKeyboardButton("ℹ️ How it Works", callback_data="help"),
         InlineKeyboardButton("🗑️ Clear Thumb", callback_data="clear")],
        [InlineKeyboardButton("📊 My Stats", callback_data="me_stats")]
    ]
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches photos and saves them as the user's thumbnail."""
    if await restricted(update, context): return
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Get the highest quality photo file_id
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    user_data["thumb_id"] = file_id
    
    text = (
        "🖼️ **Thumbnail Locked & Loaded!**\n\n"
        "Now send me any **Video** or **Document**.\n"
        "I will apply this thumbnail automatically! 🚀"
    )
    
    keyboard = [[InlineKeyboardButton("🗑️ Clear Thumbnail", callback_data="clear")]]
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The Core Engine: Handles 4GB+ files via ID reuse."""
    if await restricted(update, context): return
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    msg = update.message
    
    # 1. Check if user has a thumbnail set
    thumb_id = user_data.get("thumb_id")
    
    if not thumb_id:
        await msg.reply_text(
            "❌ **No Thumbnail Found!**\n\n"
            "Please send a photo first to set it as your thumbnail.",
            quote=True
        )
        return

    # 2. Identify Media Type
    media_id = None
    media_type = None
    original_caption = msg.caption or ""
    
    if msg.video:
        media_id = msg.video.file_id
        media_type = "video"
    elif msg.document:
        media_id = msg.document.file_id
        media_type = "document"
    else:
        return # Ignore other types

    # 3. Process (Simulated 'Processing' UI)
    status_msg = await msg.reply_text("⚡ **Applying Titanium Plating...**", quote=True)
    
    try:
        # 4. THE MAGIC: Send existing ID + Thumbnail ID
        # Why this works for 4GB: We are not uploading bytes. We tell Telegram:
        # "Take file X, and when you show it, use image Y as the cover."
        
        caption = original_caption
        if user_data["caption_mode"] and not caption:
             caption = f"📁 **Titan Processed**\n👤 {update.effective_user.first_name}"

        if media_type == "video":
            await context.bot.send_video(
                chat_id=msg.chat_id,
                video=media_id,
                thumbnail=thumb_id,
                caption=caption,
                supports_streaming=True
            )
        elif media_type == "document":
            await context.bot.send_document(
                chat_id=msg.chat_id,
                document=media_id,
                thumbnail=thumb_id,
                caption=caption
            )
            
        bot_stats["files_processed"] += 1
        await status_msg.delete()
        
    except BadRequest as e:
        logger.error(f"Telegram API Error: {e}")
        await status_msg.edit_text("❌ **Error:** Telegram couldn't attach this thumbnail. Is the image format valid?")
    except Exception as e:
        logger.error(f"General Error: {e}")
        await status_msg.edit_text("❌ **System Error.** Please try again.")

async def clear_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets user thumbnail."""
    user_id = update.effective_user.id
    get_user(user_id)["thumb_id"] = None
    
    await update.message.reply_text("🗑️ **Thumbnail Cleared!**\nSend a new photo to set a new one.")

# ---------------------------------------------------------------------------
# 🔘 CALLBACK QUERY HANDLER
# ---------------------------------------------------------------------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    user_data = get_user(user_id)
    
    await query.answer()
    
    if data == "clear":
        user_data["thumb_id"] = None
        await query.edit_message_text("🗑️ **Thumbnail Cleared.** Send a new photo!")
        
    elif data == "help":
        text = (
            "ℹ️ **Titan Help**\n\n"
            "1. Send a Photo 🖼️\n"
            "2. Send a Video/File 📁\n"
            "3. I combine them! 🪄\n\n"
            "**Why use this?**\n"
            "• Supports 4GB+ Files\n"
            "• Zero Quality Loss\n"
            "• Works for Channels"
        )
        back_btn = [[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_btn), parse_mode="Markdown")
        
    elif data == "back_start":
        # Re-render start menu (simplified)
        await start(update, context)

    elif data == "me_stats":
        status = "✅ Active" if user_data['thumb_id'] else "❌ Empty"
        text = (
            f"👤 **User Stats**\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"🖼️ Thumbnail: {status}\n"
            f"📅 Joined: {user_data['joined_at']}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

# ---------------------------------------------------------------------------
# 👑 ADMIN COMMANDS
# ---------------------------------------------------------------------------

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    uptime = str(datetime.now() - bot_stats["start_time"]).split('.')[0]
    total_users = len(users_db)
    active_thumbs = sum(1 for u in users_db.values() if u["thumb_id"])
    
    text = (
        "📊 **TITAN SYSTEM STATS**\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"🖼️ Active Thumbnails: `{active_thumbs}`\n"
        f"📂 Files Processed: `{bot_stats['files_processed']}`\n"
        f"⏱️ Uptime: `{uptime}`\n"
        f"🛠️ Maintenance: `{'ON' if maintenance_mode else 'OFF'}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    msg = update.message.text.split(" ", 1)
    if len(msg) < 2:
        await update.message.reply_text("⚠️ Usage: `/broadcast <message>`")
        return
        
    text_to_send = f"📢 **Titan Announcement**\n\n{msg[1]}"
    count = 0
    
    status_msg = await update.message.reply_text("🚀 Starting broadcast...")
    
    for uid in users_db:
        try:
            await context.bot.send_message(chat_id=uid, text=text_to_send, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05) # Flood control
        except Exception:
            pass # Ignore blocked users
            
    await status_msg.edit_text(f"✅ Broadcast complete. Sent to {count} users.")

async def admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    global maintenance_mode
    
    args = context.args
    if not args:
        await update.message.reply_text(f"Current mode: {maintenance_mode}")
        return
        
    if args[0].lower() == "on":
        maintenance_mode = True
        await update.message.reply_text("🔒 Maintenance Mode ENABLED.")
    elif args[0].lower() == "off":
        maintenance_mode = False
        await update.message.reply_text("🔓 Maintenance Mode DISABLED.")

# ---------------------------------------------------------------------------
# 🏁 MAIN EXECUTION
# ---------------------------------------------------------------------------

def main():
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your BOT_TOKEN in the script or environment variables.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # User Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear_thumb", clear_thumbnail))
    application.add_handler(MessageHandler(filters.PHOTO, handle_thumbnail))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.Document.ALL, handle_media))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Admin Handlers
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(CommandHandler("maintenance", admin_maintenance))

    print("⚡ Titan Thumbnail Bot is Online...")
    application.run_polling()

if __name__ == '__main__':
    main()
