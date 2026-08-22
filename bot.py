# --- LIBRARIES & MODULES IMPORT ---
import re         # Text cleaning aur link format match karne ke liye regex
import math       # Pagination pages calculate karne ke liye (math.ceil)
import secrets    # Unique random query ID generate karne ke liye (cache tracking)
import asyncio    # Asynchronous delays aur background timers chalane ke liye
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery
)
from pyrogram.errors import UserNotParticipant, MessageNotModified, FloodWait

# Config, Database aur UI Template files ko import kiya gaya hai
from config import API_ID, API_HASH, BOT_TOKEN, DB_CHANNEL, FSUB_CHANNEL, ADMINS
import database as db
import template as ui

# Telegram Client instance setup
bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# Search sessions ko temporary memory me rakhne ke liye cache dictionary
SEARCH_CACHE = {}

# Admin check function: verify karta hai ki message bhejne wala admin list me hai ya nahi
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


# --- AUTO DELETE HELPER FUNCTIONS ---

# Background timer: 'delay' seconds baad message ko chupchap delete karta hai
async def auto_delete_msg(client: Client, chat_id: int, message_id: int, delay: int):
    """Delete any message safely without warning"""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception:
        pass

# File result message ko delete karke user ko warning alert message bhejta hai
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
        # Alert message ko bhi 10 min baad delete kar deta hai
        asyncio.create_task(auto_delete_msg(client, chat_id, alert_msg.id, delay=600))
    except Exception as e:
        print(f"[AutoDelete Warn Error]: {e}", flush=True)


# --- FORCE SUBSCRIBE (FSUB) HELPERS ---

# FSUB channel ka invite link fetch karne ke liye
async def get_fsub_link(client: Client):
    if isinstance(FSUB_CHANNEL, int):
        try:
            chat = await client.get_chat(FSUB_CHANNEL)
            return chat.invite_link or f"https://t.me/{chat.username}"
        except Exception:
            return "https://t.me"
    return f"https://t.me/{FSUB_CHANNEL}"

# Check karta hai user ne FSUB channel join kiya hai ya nahi
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


# --- 1. BOT & DATABASE STATS COMMAND ---
# Database me total files, total users aur storage type check karne ke liye
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


# --- 2. BATCH / RANGE INDEXER COMMAND ---
# Private channel links se range me files index/save karne ke liye (e.g. /index t.me/c/123/1-100)
@bot.on_message(filters.command("index") & filters.private)
async def batch_index_url(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **Private Channel Indexing Guide:**\n\n"
            "👉 **Single Post Link:** `/index https://t.me/c/1234567890/50`\n"
            "👉 **Range Link:** `/index https://t.me/c/1234567890/10-50`\n\n"
            "*(Bot ka private channel me added aur admin hona zaroori hai)*"
        )

    link = message.command[1].strip()
    
    # Link se Channel ID aur Message Range parse karta hai
    match = re.match(r"(?:https?://)?(?:www\.)?t\.me/c/(\d+)/(\d+)(?:-(\d+))?", link)
    if not match:
        return await message.reply_text("❌ Galat private channel link format! Example: `https://t.me/c/123456789/10-50`")

    channel_id = int(f"-100{match.group(1)}")
    start_id = int(match.group(2))
    end_id = int(match.group(3)) if match.group(3) else start_id

    if start_id > end_id:
        start_id, end_id = end_id, start_id

    total_msgs = (end_id - start_id) + 1
    status_msg = await message.reply_text(f"⏳ **Indexing start ho rahi hai...**\nTotal Messages: `{total_msgs}`")

    indexed_count = 0
    skipped_count = 0

    # Ek-ek message fetch karke database me save karne ka loop
    for current_id in range(start_id, end_id + 1):
        try:
            msg = await client.get_messages(chat_id=channel_id, message_ids=current_id)
            if msg and (msg.document or msg.video or msg.audio):
                media = msg.document or msg.video or msg.audio
                file_name = getattr(media, "file_name", None) or msg.caption or "Unknown"
                saved = await db.save_file(
                    file_id=media.file_id,
                    file_name=file_name,
                    file_size=media.file_size,
                    caption=msg.caption or ""
                )
                if saved:
                    indexed_count += 1
                else:
                    skipped_count += 1
            else:
                skipped_count += 1

            # Har 20 messages ke baad progress update karta hai
            if (current_id - start_id + 1) % 20 == 0:
                await status_msg.edit_text(
                    f"⏳ **Indexing In Progress...**\n\n"
                    f"Processed: `{current_id - start_id + 1}/{total_msgs}`\n"
                    f"✅ Indexed: `{indexed_count}`\n"
                    f"⏩ Skipped/Duplicate: `{skipped_count}`"
                )
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"[Index Loop Error]: {e}", flush=True)

    await status_msg.edit_text(
        f"🎉 **Indexing Complete!**\n\n"
        f"✅ **Total Indexed:** `{indexed_count}`\n"
        f"⏩ **Skipped/Duplicate:** `{skipped_count}`"
    )


# --- 3. FORWARD MEDIA INDEXER ---
# Bot ko direct file forward karke DB me save karne ka feature
@bot.on_message(filters.private & filters.forwarded & (filters.document | filters.video | filters.audio))
async def forward_index_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return

    media = message.document or message.video or message.audio
    file_name = getattr(media, "file_name", None) or message.caption or "Unknown"
    saved = await db.save_file(
        file_id=media.file_id,
        file_name=file_name,
        file_size=media.file_size,
        caption=message.caption or ""
    )
    if saved:
        await message.reply_text(f"✅ **Saved in DB:**\n`{file_name}`")
    else:
        await message.reply_text(f"⚠️ **File already saved / duplicate:**\n`{file_name}`")


# --- 4. GROUP WELCOME HANDLER ---
# Naye user aur bot ke group join karne par welcome text bhejne ke liye
@bot.on_message(filters.group & filters.new_chat_members)
async def group_welcome_handler(client: Client, message: Message):
    for member in message.new_chat_members:
        welcome_user_text = ui.get_user_welcome_text(member.first_name, message.chat.title)
        await message.reply_text(text=welcome_user_text, reply_to_message_id=message.id)

        # Agar bot khud add hua hai to admin mangne wala message bhejega
        if member.id == client.me.id:
            welcome_text = ui.get_group_welcome_text(message.chat.title)
            welcome_buttons = ui.get_group_welcome_buttons(client.me.username)
            await message.reply_text(text=welcome_text, reply_markup=welcome_buttons, reply_to_message_id=message.id)


# --- 5. ADMIN COMMANDS: BAN & UNBAN ---
# User ko bot use karne se block ya unblock karne ke handlers
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


# --- 6. ADMIN COMMANDS: FILE DELETION ---
# Single file ya kisi movie ki saari files delete karne ke commands
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


# --- 7. START COMMAND & FILE DELIVERY ---
# Bot start karna, FSUB check karna aur deep-link ke through direct file send karna
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    first_name = message.from_user.first_name if message.from_user else "User"

    if await db.is_user_banned(user_id):
        return await message.reply_text("⛔ **Aapko bot se ban kiya gaya hai.**")

    await db.add_user(user_id)

    # Force-sub check
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

    # Deep-link se file bhejna (e.g. /start file_12345)
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
            # 4 minute (240 sec) baad file auto-delete
            asyncio.create_task(auto_delete_msg(client, user_id, sent_msg.id, delay=240))
            return

    # Normal /start message
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


# --- 8. AUTO INDEX IN DB CHANNEL ---
# Database channel me nayi file aate hi automatically database me store karna
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


# --- 9. MOVIE SEARCH HANDLER ---
# User jab koi movie/file ka naam group ya PM me type karta hai tab search perform karna
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "help", "ban", "unban", "delete", "deletefiles", "deleteall", "delall", "stats", "status", "index"]))
async def filter_search(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    chat_id = message.chat.id

    if await db.is_user_banned(user_id):
        return await message.reply_text("⛔ **Aap ban hain, bot use nahi kar sakte.**")

    # FSUB check (PM searches ke liye)
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

    # Agar koi file na mile
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

    search_msg = await message.reply_text(
        text=caption_text, 
        reply_markup=keyboard,
        reply_to_message_id=message.id
    )

    # 4.5 min (270 sec) baad search result delete karke warning bhejna
    asyncio.create_task(auto_delete_and_warn(client, chat_id, search_msg.id, first_name, user_id, delay=270))


# --- 10. CALLBACK ROUTER (BUTTON CLICKS) ---
# Next/Prev page buttons aur Search Guide popups handle karna
@bot.on_callback_query()
async def callback_router(client: Client, query: CallbackQuery):
    data = query.data
    first_name = query.from_user.first_name or "User"

    # Search Guide button click
    if data == "btn_search_guide":
        await query.answer()
        guide_text = ui.get_search_guide_text()
        guide_msg = await query.message.reply_text(text=guide_text)
        asyncio.create_task(auto_delete_msg(client, query.message.chat.id, guide_msg.id, delay=86400))
        return

    # Pagination navigation (page_queryid_pagenumber)
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

    # Inactive clicks (e.g. Title header ya Current Page count)
    elif data in ["pages_click", "header_click"]:
        await query.answer()


# --- BOT STARTUP & LIFECYCLE ---
async def main():
    # Database table initialize karna
    await db.init_db()
    await bot.start()
    print(">>> BOT IS ONLINE (CONNECTED TO TURSO DB) <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
