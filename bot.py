# =========================================================
# FILE NAME: bot.py
# =========================================================

import re
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
from pyrogram.errors import UserNotParticipant, MessageNotModified, FloodWait

# Config, Database, Broadcast aur UI Template imports
from config import API_ID, API_HASH, BOT_TOKEN, DB_CHANNEL, FSUB_CHANNEL, ADMINS
import database as db
import template as ui
from broadcast import handle_broadcast, handle_broadcast_callback

bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

SEARCH_CACHE = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# --- AUTO DELETE HELPERS ---
async def auto_delete_msg(client: Client, chat_id: int, message_id: int, delay: int):
    """Delete any message safely without warning"""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception:
        pass

async def auto_delete_and_warn(client: Client, chat_id: int, message_id: int, first_name: str, user_id: int, delay: int):
    """Wait -> Delete Message -> Send Standalone Warning Alert -> Delete Alert Later"""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
        alert_text = ui.get_deleted_alert_text(first_name, user_id)
        alert_msg = await client.send_message(
            chat_id=chat_id, 
            text=alert_text,
            disable_web_page_preview=True
        )
        asyncio.create_task(auto_delete_msg(client, chat_id, alert_msg.id, delay=600))
    except Exception as e:
        print(f"[AutoDelete Warn Error]: {e}", flush=True)

# --- FORCE SUBSCRIBE (FSUB) HELPERS ---
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

# --- 1. STATS COMMAND ---
@bot.on_message(filters.command(["stats", "status"]) & filters.private)
async def stats_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    stats = await db.get_db_stats()
    text = (
        "📊 **Bot & Database Statistics:**\n\n"
        f"📁 **Total Files in DB:** `{stats['total_files']}`\n"
        f"🗄️ **Storage Engine:** `{stats['storage_type']}`\n\n"
        f"👥 **Total Users:** `{stats['total_users']}`\n"
        f"🚫 **Banned Users:** `{stats['banned_users']}`"
    )
    await message.reply_text(text)

# --- 2. BROADCAST COMMAND ---
@bot.on_message(filters.command(["broadcast", "bcast"]) & filters.private)
async def broadcast_router(client: Client, message: Message):
    await handle_broadcast(client, message)

# --- 3. GROUP WELCOME EVENTS ---
@bot.on_message(filters.group & filters.new_chat_members)
async def group_welcome_handler(client: Client, message: Message):
    for member in message.new_chat_members:
        # Case 1: Bot khud add hua hai
        if member.id == client.me.id:
            welcome_text = ui.get_group_welcome_text(message.chat.title)
            welcome_buttons = ui.get_group_welcome_buttons(client.me.username)
            await message.reply_text(
                text=welcome_text,
                reply_markup=welcome_buttons,
                reply_to_message_id=message.id
            )
        # Case 2: Koi doosra user ya bot add hua hai
        else:
            welcome_user_text = ui.get_user_welcome_text(member.first_name, member.id, message.chat.title)
            await message.reply_text(
                text=welcome_user_text,
                reply_to_message_id=message.id
            )

# --- 4. ADMIN COMMANDS: BAN & UNBAN ---
@bot.on_message(filters.command("ban") & (filters.private | filters.group))
async def ban_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_id = int(message.command[1])
        except ValueError:
            return await message.reply_text("⚠️ Sahi numeric user ID dalein.")

    if not target_id:
        return await message.reply_text("⚠️ Usage: `/ban user_id` ya message ko reply karein.")

    await db.ban_user(target_id)
    await message.reply_text(f"🚫 User `{target_id}` ko ban kar diya gaya hai.")

@bot.on_message(filters.command("unban") & (filters.private | filters.group))
async def unban_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_id = int(message.command[1])
        except ValueError:
            return await message.reply_text("⚠️ Sahi numeric user ID dalein.")

    if not target_id:
        return await message.reply_text("⚠️ Usage: `/unban user_id` ya message ko reply karein.")

    await db.unban_user(target_id)
    await message.reply_text(f"✅ User `{target_id}` ko unban kar diya gaya hai.")

# --- 5. ADMIN COMMANDS: FILE DELETION & CLEAR ALL ---
@bot.on_message(filters.command("delete"))
async def delete_single_cmd(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if message.reply_to_message:
        target_msg = message.reply_to_message
        media = target_msg.document or target_msg.video or target_msg.audio
        if media:
            deleted = await db.delete_single_file(file_id=media.file_id)
            if deleted:
                return await message.reply_text("🗑️ File database se delete kar di gayi hai.")
            return await message.reply_text("⚠️ File database me nahi mili.")
        elif target_msg.text or target_msg.caption:
            name_query = target_msg.text or target_msg.caption
            deleted = await db.delete_single_file(file_name=name_query)
            if deleted:
                return await message.reply_text(f"🗑️ `{name_query}` database se delete kar di gayi hai.")
            return await message.reply_text("⚠️ File database me nahi mili.")

    if len(message.command) > 1:
        name_query = message.text.split(None, 1)[1].strip()
        count = await db.delete_single_file(file_name=name_query)
        if count:
            return await message.reply_text(f"🗑️ `{name_query}` file delete kar di gayi hai.")
        return await message.reply_text("⚠️ File database me nahi mili.")

    await message.reply_text("⚠️ File ko reply karke `/delete` ya `/delete Movie_Name` likhein.")

@bot.on_message(filters.command(["deletefiles", "deleteall", "delall"]))
async def delete_files_cmd(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text("⚠️ Movie ka naam likhein: `/deletefiles Movie_Name`")

    movie_name = message.text.split(None, 1)[1].strip()
    status_msg = await message.reply_text(f"🔍 `{movie_name}` ki files delete ho rahi hain...")
    deleted_count = await db.delete_files_by_name(movie_name)
    await status_msg.edit_text(f"✅ `{movie_name}` se judi **{deleted_count} files** delete kar di gayi hain.")

# Poori Database Clear Karne Ka Command (/clearall)
@bot.on_message(filters.command(["clearall", "flushdb", "cleardb"]) & filters.private)
async def clear_db_cmd(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    confirm_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ YES, DELETE ALL", callback_data="confirm_clear_all_db"),
            InlineKeyboardButton("❌ CANCEL", callback_data="cancel_clear_db")
        ]
    ])
    await message.reply_text(
        "⚠️ **WARNING:** Kya aap sach me database ki **SAARI FILES** delete karna chahte hain?\n\nYeh action wapas nahi liya ja sakta!",
        reply_markup=confirm_markup
    )

# --- 6. START COMMAND & FILE DELIVERY ---
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    first_name = message.from_user.first_name if message.from_user else "User"

    if await db.is_user_banned(user_id):
        return await message.reply_text("⛔ **Aapko bot se ban kiya gaya hai.**")

    await db.add_user(user_id)

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

    # Deliver file with clean warning caption (No extra buttons)
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
            # Auto delete file after exactly 60 seconds (1 minute)
            asyncio.create_task(auto_delete_msg(client, user_id, sent_msg.id, delay=60))
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

    if sent_start:
        asyncio.create_task(auto_delete_msg(client, user_id, sent_start.id, delay=86400))

# --- 7. AUTO INDEX IN DB CHANNEL (DUPLICATE FILTER) ---
@bot.on_message(filters.chat(DB_CHANNEL) & (filters.document | filters.video | filters.audio))
async def auto_index(client: Client, message: Message):
    media = message.document or message.video or message.audio
    if not media:
        return
    file_name = getattr(media, "file_name", None) or message.caption or "Unknown"
    
    is_saved = await db.save_file(
        file_id=media.file_id,
        file_name=file_name,
        file_size=media.file_size,
        caption=message.caption or ""
    )
    if is_saved:
        print(f"[INDEXED]: {file_name}", flush=True)
    else:
        print(f"[DUPLICATE SKIPPED]: {file_name}", flush=True)

# --- 8. MOVIE SEARCH HANDLER ---
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "help", "ban", "unban", "delete", "deletefiles", "deleteall", "delall", "clearall", "flushdb", "cleardb", "stats", "status", "broadcast", "bcast"]))
async def filter_search(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    chat_id = message.chat.id

    if await db.is_user_banned(user_id):
        return await message.reply_text("⛔ **Aap ban hain, bot use nahi kar sakte.**")

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

    # Exact curved bold-italic search caption
    caption_text = ui.get_search_caption(first_name, user_id, query)
    keyboard = ui.build_pagination_keyboard(files, query_id, 1, total_pages, query, client.me.username)

    search_msg = await message.reply_text(
        text=caption_text, 
        reply_markup=keyboard,
        reply_to_message_id=message.id
    )

    asyncio.create_task(auto_delete_and_warn(client, chat_id, search_msg.id, first_name, user_id, delay=270))

# --- 9. CALLBACK ROUTER ---
@bot.on_callback_query()
async def callback_router(client: Client, query: CallbackQuery):
    data = query.data
    first_name = query.from_user.first_name or "User"
    user_id = query.from_user.id

    # Broadcast confirmation callback
    if data.startswith("bcast_"):
        await handle_broadcast_callback(client, query)
        return

    # Clear All Database Confirmation
    elif data == "confirm_clear_all_db":
        if not is_admin(query.from_user.id):
            return await query.answer("⛔ Access Denied!", show_alert=True)
        
        await query.message.edit_text("⏳ Saari files delete ho rahi hain, kripya wait karein...")
        deleted_count = await db.clear_all_files()
        await query.message.edit_text(f"✅ **Database poori tarah clear ho gaya hai!**\n\n🗑️ Total **{deleted_count} files** delete ki gayi hain.")
        await query.answer()
        return

    elif data == "cancel_clear_db":
        await query.message.edit_text("❌ Database clear cancel kar diya gaya.")
        await query.answer()
        return

    elif data == "btn_search_guide":
        await query.answer()
        guide_text = ui.get_search_guide_text()
        guide_msg = await query.message.reply_text(text=guide_text)
        asyncio.create_task(auto_delete_msg(client, query.message.chat.id, guide_msg.id, delay=86400))
        return

    # Pagination navigation
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

            caption_text = ui.get_search_caption(first_name, user_id, search_query)
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

# --- MAIN RUNNER ---
async def main():
    await db.init_db()
    await bot.start()
    print(">>> BOT IS ONLINE (CONNECTED TO TURSO DB) <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
