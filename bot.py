import math
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, CHANNELS, FORCE_SUB_CHANNEL
from database import db_instance
from template import Script

logging.basicConfig(level=logging.INFO)

app = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

async def is_subscribed(client, user_id):
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        user = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        if user.status in ["banned", "left"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    await db_instance.add_user(message.from_user.id)
    
    if not await is_subscribed(client, message.from_user.id):
        buttons = [
            [InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@', '')}")],
            [InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")]
        ]
        await message.reply_text(Script.FORCE_SUB_TEXT, reply_markup=InlineKeyboardMarkup(buttons))
        return

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@', '')}" if FORCE_SUB_CHANNEL else "https://t.me/"), 
         InlineKeyboardButton("💬 Support Group", url="https://t.me/")]
    ])
    await message.reply_text(
        text=Script.START_TEXT.format(message.from_user.first_name),
        reply_markup=buttons,
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex("check_sub"))
async def check_sub_handler(client, query: CallbackQuery):
    if not await is_subscribed(client, query.from_user.id):
        await query.answer("❌ Aapne abhi tak channel join nahi kiya hai!", show_alert=True)
        return
    await query.message.delete()
    await query.message.reply_text("✅ Verification Successful! Ab aap koi bhi movie search kar sakte hain.")

@app.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_indexer(client, message: Message):
    media = message.document or message.video or message.audio
    if media:
        file_data = {
            "file_id": media.file_id,
            "file_name": media.file_name or "Unknown Movie",
            "file_size": media.file_size,
            "mime_type": getattr(media, "mime_type", "")
        }
        await db_instance.save_file(file_data)

def create_search_markup(results, query, page=1):
    buttons = []
    # Header Button (Movie Title Banner)
    buttons.append([InlineKeyboardButton(f"🎬 {query.title()} 🎬", callback_data="ignore")])
    
    PER_PAGE = 10
    total_results = len(results)
    total_pages = math.ceil(total_results / PER_PAGE) or 1
    
    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    page_files = results[start_idx:end_idx]
    
    # Size • Filename format
    for file in page_files:
        size_str = format_size(file['file_size'])
        btn_text = f"{size_str} • {file['file_name']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"file#{file['file_id']}")])
        
    # Pagination Row
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⏪ Previous", callback_data=f"page#{query}#{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="pages_count"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ⏭️", callback_data=f"page#{query}#{page+1}"))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.text & ~filters.command(["start", "help", "about"]))
async def auto_filter(client, message: Message):
    if message.chat.type.name == "PRIVATE":
        if not await is_subscribed(client, message.from_user.id):
            buttons = [
                [InlineKeyboardButton("📢 Join Update Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@', '')}")],
                [InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")]
            ]
            await message.reply_text(Script.FORCE_SUB_TEXT, reply_markup=InlineKeyboardMarkup(buttons))
            return

    query = message.text.strip()
    if len(query) < 2:
        return
    
    results = await db_instance.search_media(query)
    if not results:
        return
    
    reply_markup = create_search_markup(results, query, page=1)
    msg_text = f"Title : <b>{query.title()}</b>\nYour Files is Ready Now"
    
    await message.reply_text(
        text=msg_text,
        reply_markup=reply_markup,
        quote=True
    )

@app.on_callback_query(filters.regex(r"^page#"))
async def pagination_handler(client, query: CallbackQuery):
    data_parts = query.data.split("#")
    search_query = data_parts[1]
    page_num = int(data_parts[2])
    
    results = await db_instance.search_media(search_query)
    if not results:
        await query.answer("❌ No files found!", show_alert=True)
        return
        
    reply_markup = create_search_markup(results, search_query, page=page_num)
    try:
        await query.message.edit_reply_markup(reply_markup=reply_markup)
    except Exception:
        pass
    await query.answer()

@app.on_callback_query(filters.regex(r"^file#"))
async def send_file_handler(client, query: CallbackQuery):
    if not await is_subscribed(client, query.from_user.id):
        await query.answer("⚠️ Pehle update channel join karein!", show_alert=True)
        return
    
    file_id = query.data.split("#", 1)[1]
    await client.send_cached_media(
        chat_id=query.from_user.id,
        file_id=file_id
    )
    await query.answer("✅ Movie file aapke inbox me bhej di gayi hai!", show_alert=True)

@app.on_callback_query(filters.regex(r"^(ignore|pages_count)$"))
async def ignore_handler(client, query: CallbackQuery):
    await query.answer()

def format_size(size):
    if not size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

if __name__ == "__main__":
    app.run()
