import math
import secrets
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery
)
from pyrogram.errors import UserNotParticipant, MessageNotModified
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

# --- GENERAL AUTO DELETE HELPER ---
async def auto_delete_msg(client: Client, chat_id: int, message_id: int, delay: int):
    """Delete any message safely without warning"""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception:
        pass

# --- DELETE TARGET & SEND WARNING ALERT ---
async def auto_delete_and_warn(client: Client, chat_id: int, message_id: int, first_name: str, user_id: int, delay: int):
    """Wait -> Delete Message -> Send Standalone Warning Alert -> Delete Alert Later"""
    await asyncio.sleep(delay)
    try:
        # 1. Target message delete karo
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
        
        # 2. Warning message direct send karo (No box/reply header)
        alert_text = ui.get_deleted_alert_text(first_name, user_id)
        alert_msg = await client.send_message(
            chat_id=chat_id, 
            text=alert_text,
            disable_web_page_preview=True
        )
        
        # 3. Warning Alert 10 minute (600s) baad delete karo
        asyncio.create_task(auto_delete_msg(client, chat_id, alert_msg.id, delay=600))
    except Exception as e:
        print(f"[AutoDelete Warn Error]: {e}", flush=True)

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

# --- BOT ADDED TO GROUP WELCOME EVENT ---
@bot.on_message(filters.group & filters.new_chat_members)
async def group_welcome(client: Client, message: Message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            welcome_text = ui.get_group_welcome_text(message.chat.title)
            welcome_buttons = ui.get_group_welcome_buttons(client.me.username)
            await client.send_message(
                chat_id=message.chat.id,
                text=welcome_text,
                reply_markup=welcome_buttons
            )
            break

# --- START COMMAND (BOT PRIVATE CHAT) ---
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
                reply_markup=buttons,
                reply_to_message_id=message.id
            )
        except Exception:
            return await message.reply_text(
                "⚠️ **Access Denied!**\n\nPehle hamara update channel join karein, fir **Try Again** par click karein.",
                reply_markup=buttons,
                reply_to_message_id=message.id
            )

    # Group Button Se Aayi Hui File (Group Deep Link):
    # Rule: 4 min me file delete hogi lekin WARNING NAHI AAYEGI
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
            # Sirf file delete hogi (No warning message)
            asyncio.create_task(auto_delete_msg(client, user_id, sent_msg.id, delay=240))
            return

    caption_text = ui.get_start_text(first_name)
    markup = ui.get_start_buttons(client.me.username)

    sent_start = None
    try:
        sent_start = await message.reply_photo(
            photo=ui.START_PIC,
            caption=caption_text,
            reply_markup=markup
        )
    except Exception:
        sent_start = await message.reply_text(text=caption_text, reply_markup=markup)

    # Start message deletes after 1 day (86400 seconds)
    if sent_start:
        asyncio.create_task(auto_delete_msg(client, user_id, sent_start.id, delay=86400))

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

# --- SEARCH HANDLER (BOX / QUOTE REPLY) ---
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "help"]))
async def filter_search(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    chat_id = message.chat.id

    if message.chat.type.value == "private" and not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        btn = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text(
            "⚠️ Pehle hamara update channel join karein.", 
            reply_markup=InlineKeyboardMarkup(btn),
            reply_to_message_id=message.id
        )

    query = message.text.strip()
    total_results = await db.count_files(query)

    # Not Found Message with Quote Box (5 minutes / 300s auto delete)
    if total_results == 0:
        no_res_msg = await message.reply_text(
            text=ui.get_no_results_text(),
            reply_to_message_id=message.id
        )
        asyncio.create_task(auto_delete_msg(client, chat_id, no_res_msg.id, delay=300))
        return

    query_id = secrets.token_hex(4)
    SEARCH_CACHE[query_id] = query

    total_pages = math.ceil(total_results / 10)
    files = await db.search_files(query, offset=0, limit=10)

    caption_text = ui.get_search_caption(first_name, query)
    keyboard = ui.build_pagination_keyboard(files, query_id, 1, total_pages, query, client.me.username)

    # Search result message with Quote Box (4.5 minutes / 270s auto delete)
    search_msg = await message.reply_text(
        text=caption_text, 
        reply_markup=keyboard,
        reply_to_message_id=message.id
    )

    # Buttons 4.5 min me delete honge aur Warning Alert aayega
    asyncio.create_task(auto_delete_and_warn(client, chat_id, search_msg.id, first_name, user_id, delay=270))

# --- CALLBACK ROUTER ---
@bot.on_callback_query()
async def callback_router(client: Client, query: CallbackQuery):
    data = query.data
    first_name = query.from_user.first_name or "User"

    # Search Guide Message Button (Auto-deletes in 1 Day / 86400s)
    if data == "btn_search_guide":
        await query.answer()
        guide_text = ui.get_search_guide_text()
        guide_msg = await query.message.reply_text(text=guide_text)
        asyncio.create_task(auto_delete_msg(client, query.message.chat.id, guide_msg.id, delay=86400))
        return

    elif data.startswith("page_"):
        try:
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
        except MessageNotModified:
            pass
        except Exception as e:
            print(f"Pagination Error: {e}", flush=True)
        finally:
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
