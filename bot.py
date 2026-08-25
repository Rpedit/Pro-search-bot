from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, BOT_TOKEN, INDEX_CHANNELS, FORCE_SUB_CHANNEL, FORCE_SUB_INVITE
from database import save_file, search_db, get_file
from template import get_search_message, build_pagination_keyboard

bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

async def is_subscribed(client: Client, user_id: int) -> bool:
    """Channel membership verify karta hai"""
    if not FORCE_SUB_CHANNEL:
        return True
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status not in ["kicked", "left"]
    except UserNotParticipant:
        return False
    except Exception:
        return True

def get_fsub_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Updates Channel", url=FORCE_SUB_INVITE)],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot.me.username}?start=start")]
    ])

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nBot ko use karne ke liye pehle official updates channel join karein.",
            reply_markup=get_fsub_markup()
        )
    await message.reply_text(f"Hello {message.from_user.mention}! Koi bhi Movie ya Series ka naam likh kar send karein.")

# Channels se auto-indexing handler
@bot.on_message(filters.chat(INDEX_CHANNELS) & (filters.document | filters.video | filters.audio))
async def auto_index(client: Client, message: Message):
    media = message.document or message.video or message.audio
    if media:
        await save_file(media)

# Search Query handler
@bot.on_message(filters.text & filters.private)
async def search_handler(client: Client, message: Message):
    if message.text.startswith("/"):
        return

    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nFiles search karne ke liye pehle channel join karein.",
            reply_markup=get_fsub_markup()
        )

    query = message.text.strip()
    results = await search_db(query)

    if not results:
        return await message.reply_text(f"❌ **'{query}'** ke liye koi file nahi mili.")

    caption = get_search_message(query, message.from_user.mention)
    markup = build_pagination_keyboard(results, query, page=1)
    await message.reply_text(caption, reply_markup=markup)

# Pagination & File Delivery Buttons Handler
@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "pages_info":
        return await query.answer()

    if data.startswith("nav_"):
        parts = data.split("_")
        page = int(parts[-1])
        search_text = "_".join(parts[1:-1])
        
        results = await search_db(search_text)
        if not results:
            return await query.answer("Koi files nahi mili!", show_alert=True)

        markup = build_pagination_keyboard(results, search_text, page=page)
        await query.message.edit_reply_markup(reply_markup=markup)
        await query.answer()

    elif data.startswith("get_"):
        file_id = data.split("get_", 1)[1]
        file_data = await get_file(file_id)

        if not file_data:
            return await query.answer("File database me nahi mili!", show_alert=True)

        await query.answer("Sending file...")
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_data["file_id"],
            caption=f"📁 **{file_data['file_name']}**"
        )
