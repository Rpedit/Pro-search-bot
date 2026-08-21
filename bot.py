import math
import secrets
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    Message, 
    CallbackQuery, 
    InlineQuery
)
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, BOT_TOKEN, DB_CHANNEL, FSUB_CHANNEL
import database as db
import template as ui

bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

SEARCH_CACHE = {}

# 60 Seconds Background Timer for File Auto-Deletion
async def auto_delete_file(client: Client, chat_id: int, message_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception:
        pass

async def get_fsub_link(client: Client):
    if isinstance(FSUB_CHANNEL, int):
        try:
            chat = await client.get_chat(FSUB_CHANNEL)
            return chat.invite_link or f"https://t.me/{chat.username}"
        except Exception:
            return "https://t.me"
    return f"https://t.me/{FSUB_CHANNEL}"

async def is_subscribed(client: Client, user_id: int):
    if not FSUB_CHANNEL:
        return True
    try:
        member = await client.get_chat_member(FSUB_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except UserNotParticipant:
        return False
    except Exception:
        return True

# --- START COMMAND ---
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    first_name = message.from_user.first_name if message.from_user else "User"
    await db.add_user(user_id)

    # Force Subscribe Check
    if not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        buttons = ui.get_fsub_buttons(invite_link, client.me.username)
        try:
            return await message.reply_photo(
                photo=ui.START_PIC,
                caption="⚠️ **Access Denied!**\n\nPehle hamara update channel join karein, fir **Try Again** par click karein.",
                reply_markup=buttons
            )
        except Exception:
            return await message.reply_text(
                "⚠️ **Access Denied!**\n\nPehle hamara update channel join karein, fir **Try Again** par click karein.",
                reply_markup=buttons
            )

    # Deep Link Handler (Direct Send with Exact Warning Caption + 1-Min Auto Delete)
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        db_id = message.command[1].replace("file_", "")
        file_data = await db.get_file_by_id(db_id)
        if file_data:
            caption_text = ui.get_file_caption(file_data["file_name"])
            sent_msg = await client.send_cached_media(
                chat_id=user_id,
                file_id=file_data["file_id"],
                caption=caption_text
            )
            asyncio.create_task(auto_delete_file(client, user_id, sent_msg.id, delay=60))
            return

    caption_text = ui.get_start_text(first_name)
    markup = ui.get_start_buttons(client.me.username)

    try:
        await message.reply_photo(
            photo=ui.START_PIC,
            caption=caption_text,
            reply_markup=markup
        )
    except Exception:
        await message.reply_text(text=caption_text, reply_markup=markup)

# --- AUTO INDEX IN DB CHANNEL ---
@bot.on_message(filters.chat(DB_CHANNEL) & (filters.document | filters.video | filters.audio))
async def auto_index(client: Client, message: Message):
    media = message.document or message.video or message.audio
    if not media:
        return
    file_name = getattr(media, "file_name", None) or message.caption or "Unknown"
    await db.save_file(
        file_id=media.file_id,
        file_name=file_name,
        file_size=media.file_size,
        caption=message.caption or ""
    )
    print(f"[INDEXED]: {file_name}", flush=True)

# --- SEARCH HANDLER ---
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "help"]))
async def filter_search(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"

    if message.chat.type.value == "private" and not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        btn = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text("⚠️ Pehle hamara update channel join karein.", reply_markup=InlineKeyboardMarkup(btn))

    query = message.text.strip()
    total_results = await db.count_files(query)

    if total_results == 0:
        return await message.reply_text(
            f"❌ **No results found for:** `{query}`\n\n"
            "💡 **Tips:**\n"
            "• Google par spelling verify karein\n"
            "• Year ya season hata kar search karein"
        )

    query_id = secrets.token_hex(4)
    SEARCH_CACHE[query_id] = query

    total_pages = math.ceil(total_results / 10)
    files = await db.search_files(query, offset=0, limit=10)

    caption_text = ui.get_search_caption(first_name, query)
    keyboard = ui.build_pagination_keyboard(files, query_id, 1, total_pages, query, client.me.username)

    await message.reply_text(text=caption_text, reply_markup=keyboard)

# --- PAGINATION CALLBACK ROUTER ---
@bot.on_callback_query()
async def callback_router(client: Client, query: CallbackQuery):
    data = query.data
    first_name = query.from_user.first_name or "User"

    if data.startswith("page_"):
        _, query_id, page_str = data.split("_")
        page = int(page_str)
        search_query = SEARCH_CACHE.get(query_id)

        if not search_query:
            return await query.answer("⚠️ Session Expired! Please search again.", show_alert=True)

        total_results = await db.count_files(search_query)
        total_pages = math.ceil(total_results / 10)
        offset = (page - 1) * 10
        files = await db.search_files(search_query, offset=offset, limit=10)

        caption_text = ui.get_search_caption(first_name, search_query)
        keyboard = ui.build_pagination_keyboard(files, query_id, page, total_pages, search_query, client.me.username)

        await query.message.edit_text(text=caption_text, reply_markup=keyboard)
        await query.answer()

    elif data in ["pages_click", "header_click"]:
        await query.answer()

async def main():
    await db.init_db()
    await bot.start()
    print(">>> BOT IS ONLINE AND LISTENING <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
