import re
import math
import secrets
import asyncio
import aiohttp
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery
)
from pyrogram.errors import UserNotParticipant, MessageNotModified, FloodWait
from config import (
    API_ID, 
    API_HASH, 
    BOT_TOKEN, 
    DB_CHANNEL, 
    FSUB_CHANNEL, 
    ADMINS, 
    SHORTENER_API, 
    SHORTENER_URL
)
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

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# --- SHORTENER HELPER ---
async def get_shortlink(url: str) -> str:
    if not SHORTENER_API or not SHORTENER_URL:
        return url
    try:
        api_endpoint = f"https://{SHORTENER_URL}/api?api={SHORTENER_API}&url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint, timeout=10) as res:
                data = await res.json()
                if data.get("status") == "success" or "shortenedUrl" in data:
                    return data.get("shortenedUrl") or data.get("url")
    except Exception as e:
        print(f"[Shortener Error]: {e}", flush=True)
    return url

# --- AUTO DELETE HELPERS ---
async def auto_delete_msg(client: Client, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)
    except Exception:
        pass

async def auto_delete_and_warn(client: Client, chat_id: int, message_id: int, first_name: str, user_id: int, delay: int):
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

# --- FSUB HELPERS ---
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

# --- 2. FORWARD DETECTOR (PRIVATE CHANNELS) ---
@bot.on_message(filters.forwarded & filters.private)
async def forward_channel_detector(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return

    if not message.forward_from_chat:
        return await message.reply_text("⚠️ Ye message kisi channel ka nahi hai.")

    fwd_chat = message.forward_from_chat
    last_msg_id = message.forward_from_message_id

    btn = [[
        InlineKeyboardButton(
            "⚡ Index All Files Now", 
            callback_data=f"idx_{fwd_chat.id}_{last_msg_id}"
        )
    ]]

    await message.reply_text(
        f"📥 **Private Channel Detected!**\n\n"
        f"📢 **Channel Title:** `{fwd_chat.title}`\n"
        f"🆔 **Channel ID:** `{fwd_chat.id}`\n"
        f"🔢 **Forwarded Message ID:** `{last_msg_id}`\n\n"
        f"👉 _Niche button dabayein ya command use karein:_\n"
        f"`/index {fwd_chat.id}`",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# --- 3. BATCH & LINK INDEX COMMAND ---
@bot.on_message(filters.command("index") & filters.private)
async def batch_index_url(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **Private Channel Indexing Guide:**\n\n"
            "👉 **Forward Method:** Channel se bot ko 1 message forward karein.\n"
            "👉 **Full Channel:** `/index -1001234567890`\n"
            "👉 **Range Link:** `/index https://t.me/c/1234567890/10-50`\n\n"
            "*(Bot ka private channel me admin hona zaroori hai)*"
        )

    arg = message.command[1].strip()
    channel_id = None
    start_id = 1
    end_id = None

    match = re.match(r"(?:https?://)?(?:www\.)?t\.me/c/(\d+)/(\d+)(?:-(\d+))?", arg)
    if match:
        channel_id = int(f"-100{match.group(1)}")
        start_id = int(match.group(2))
        end_id = int(match.group(3)) if match.group(3) else start_id
    else:
        try:
            channel_id = int(arg)
            if len(message.command) > 2:
                start_id = int(message.command[2])
            if len(message.command) > 3:
                end_id = int(message.command[3])
        except ValueError:
            return await message.reply_text("❌ Galat format! Channel ID numeric honi chahiye.")

    await run_indexing_task(client, message.chat.id, channel_id, start_id, end_id)

async def run_indexing_task(client: Client, chat_id: int, channel_id: int, start_id: int = 1, end_id: int = None):
    try:
        chat = await client.get_chat(channel_id)
    except Exception as e:
        return await client.send_message(
            chat_id, 
            f"❌ **Error:** Bot channel me access nahi kar pa raha hai. Admin privileges check karein.\n`{e}`"
        )

    status_msg = await client.send_message(
        chat_id, 
        f"⏳ **Indexing Started for:** `{chat.title}`\n🆔 `{channel_id}`..."
    )

    indexed_count = 0
    skipped_count = 0
    total_scanned = 0

    try:
        # End id provided hone par range scan
        if end_id:
            if start_id > end_id:
                start_id, end_id = end_id, start_id
            for current_id in range(start_id, end_id + 1):
                try:
                    msg = await client.get_messages(chat_id=channel_id, message_ids=current_id)
                    total_scanned += 1
                    if msg and (msg.document or msg.video or msg.audio):
                        media = msg.document or msg.video or msg.audio
                        file_name = getattr(media, "file_name", None) or msg.caption or f"file_{msg.id}"
                        saved = await db.save_file(
                            file_id=media.file_id,
                            file_name=file_name,
                            file_size=media.file_size,
                            caption=msg.caption or "",
                            channel_id=channel_id,
                            message_id=msg.id
                        )
                        if saved:
                            indexed_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1

                    if total_scanned % 25 == 0:
                        await status_msg.edit_text(
                            f"⏳ **Indexing In Progress...**\n\n"
                            f"📂 Channel: `{chat.title}`\n"
                            f"🔍 Checked: `{total_scanned}`\n"
                            f"✅ Saved: `{indexed_count}`\n"
                            f"⏩ Duplicates: `{skipped_count}`"
                        )
                        await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception:
                    pass
        else:
            # Full Channel Crawl
            async for msg in client.get_chat_history(channel_id):
                total_scanned += 1
                if msg and (msg.document or msg.video or msg.audio):
                    media = msg.document or msg.video or msg.audio
                    file_name = getattr(media, "file_name", None) or msg.caption or f"file_{msg.id}"
                    saved = await db.save_file(
                        file_id=media.file_id,
                        file_name=file_name,
                        file_size=media.file_size,
                        caption=msg.caption or "",
                        channel_id=channel_id,
                        message_id=msg.id
                    )
                    if saved:
                        indexed_count += 1
                    else:
                        skipped_count += 1

                if total_scanned % 30 == 0:
                    try:
                        await status_msg.edit_text(
                            f"⚡ **Indexing Channel History...**\n\n"
                            f"📂 Channel: `{chat.title}`\n"
                            f"🔍 Scanned: `{total_scanned}`\n"
                            f"✅ Saved: `{indexed_count}`\n"
                            f"⏩ Duplicates: `{skipped_count}`"
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        print(f"[Index Loop Error]: {e}", flush=True)

    await status_msg.edit_text(
        f"🎉 **Indexing Complete!**\n\n"
        f"📂 **Channel:** `{chat.title}`\n"
        f"🔍 **Total Checked:** `{total_scanned}`\n"
        f"✅ **Saved in DB:** `{indexed_count}`\n"
        f"⏩ **Duplicates/Skipped:** `{skipped_count}`"
    )

# --- 4. LIVE AUTO-INDEX IN ANY CHANNEL WHERE BOT IS ADMIN ---
@bot.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def live_auto_index(client: Client, message: Message):
    media = message.document or message.video or message.audio
    if not media:
        return
    file_name = getattr(media, "file_name", None) or message.caption or f"file_{message.id}"
    await db.save_file(
        file_id=media.file_id,
        file_name=file_name,
        file_size=media.file_size,
        caption=message.caption or "",
        channel_id=message.chat.id,
        message_id=message.id
    )
    print(f"[LIVE INDEXED]: {file_name} from {message.chat.title}", flush=True)

# --- 5. GROUP WELCOME EVENTS ---
@bot.on_message(filters.group & filters.new_chat_members)
async def group_welcome_handler(client: Client, message: Message):
    for member in message.new_chat_members:
        welcome_user_text = ui.get_user_welcome_text(member.first_name, message.chat.title)
        await message.reply_text(text=welcome_user_text, reply_to_message_id=message.id)

        if member.id == client.me.id:
            welcome_text = ui.get_group_welcome_text(message.chat.title)
            welcome_buttons = ui.get_group_welcome_buttons(client.me.username)
            await message.reply_text(text=welcome_text, reply_markup=welcome_buttons, reply_to_message_id=message.id)

# --- 6. ADMIN COMMANDS: BAN & UNBAN ---
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

# --- 7. ADMIN COMMANDS: DELETE & DELETEFILES ---
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

# --- 8. START COMMAND ---
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

    # Deep-link file delivery
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

    if sent_start:
        asyncio.create_task(auto_delete_msg(client, user_id, sent_start.id, delay=86400))

# --- 9. SEARCH HANDLER ---
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "help", "support", "ban", "unban", "delete", "deletefiles", "deleteall", "delall", "stats", "status", "index"]))
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
            reply_markup=ui.get_no_results_buttons(),
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

    asyncio.create_task(auto_delete_and_warn(client, chat_id, search_msg.id, first_name, user_id, delay=270))

# --- 10. CALLBACK ROUTER ---
@bot.on_callback_query()
async def callback_router(client: Client, query: CallbackQuery):
    data = query.data
    first_name = query.from_user.first_name or "User"
    user_id = query.from_user.id

    if data.startswith("idx_"):
        if not is_admin(user_id):
            return await query.answer("⛔ Sirf Admins ye use kar sakte hain.", show_alert=True)
        
        parts = data.split("_")
        ch_id = int(parts[1])
        await query.answer("Indexing Started!")
        await query.message.delete()
        return await run_indexing_task(client, query.message.chat.id, ch_id)

    elif data == "btn_search_guide":
        await query.answer()
        guide_text = ui.get_search_guide_text()
        guide_msg = await query.message.reply_text(text=guide_text)
        asyncio.create_task(auto_delete_msg(client, query.message.chat.id, guide_msg.id, delay=86400))
        return

    elif data.startswith("file_"):
        db_id = data.replace("file_", "")
        file_data = await db.get_file_by_id(db_id)
        if not file_data:
            return await query.answer("❌ File database me nahi mili!", show_alert=True)
            
        await query.answer("Sending File...")
        caption_text = ui.get_file_caption(file_data["file_name"])
        try:
            sent_msg = await client.send_cached_media(
                chat_id=user_id,
                file_id=file_data["file_id"],
                caption=caption_text
            )
            asyncio.create_task(auto_delete_msg(client, user_id, sent_msg.id, delay=240))
        except Exception:
            await query.answer(f"Pehle bot ke PM me @{client.me.username} ko /start karein.", show_alert=True)
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
    print(">>> BOT IS ONLINE (CONNECTED TO TURSO 9GB DB) <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
