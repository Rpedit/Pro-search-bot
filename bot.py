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
from config import API_ID, API_HASH, BOT_TOKEN, DB_CHANNEL, FSUB_CHANNEL, ADMINS
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
CURRENT_SKIP = 0
INDEX_RUNNING = False

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

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
@bot.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    stats = await db.get_db_stats()
    text = (
        "📊 **Bot & Database Statistics:**\n\n"
        f"📁 **Total Files in DB:** `{stats['total_files']}`\n"
        f"├─ 🗄️ **Database 1 (Primary):** `{stats['db1_files']}` files\n"
        f"└─ 🗄️ **Database 2 (Backup):** `{stats['db2_files']}` files\n\n"
        f"🔘 **Current Active Saving DB:** `{stats['active_db']}`\n\n"
        f"👥 **Total Users:** `{stats['total_users']}`\n"
        f"🚫 **Banned Users:** `{stats['banned_users']}`"
    )
    await message.reply_text(text)

# --- 2. SET SKIP COMMAND ---
@bot.on_message(filters.command("setskip") & filters.private)
async def set_skip_handler(client: Client, message: Message):
    global CURRENT_SKIP
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text(
            f"⚠️ **Skip Number Likhein:**\n👉 `/setskip 2000`\n\n📌 **Current Skip:** `{CURRENT_SKIP}`"
        )

    try:
        CURRENT_SKIP = int(message.command[1])
        await message.reply_text(
            f"✅ **Skip Count Set:** `{CURRENT_SKIP}`\nAb `/index` Msg ID `{CURRENT_SKIP}` se aage start hoga."
        )
    except ValueError:
        await message.reply_text("⚠️ Sahi numeric number enter karein.")

# --- 3. CANCEL INDEX COMMAND ---
@bot.on_message(filters.command("cancel") & filters.private)
async def cancel_index_handler(client: Client, message: Message):
    global INDEX_RUNNING
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if not INDEX_RUNNING:
        return await message.reply_text("⚠️ Koi indexing active nahi hai.")

    INDEX_RUNNING = False
    await message.reply_text("🛑 **Stopping Indexing...** Process cancel kiya ja raha hai.")

# --- 4. INDEX COMMAND (FORWARD REPLY & CHANNEL TARGET) ---
@bot.on_message(filters.command("index") & filters.private)
async def bulk_index_handler(client: Client, message: Message):
    global CURRENT_SKIP, INDEX_RUNNING
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if INDEX_RUNNING:
        return await message.reply_text("⚠️ Indexing pehle se chal rahi hai! Rokne ke liye `/cancel` likhein.")

    chat_target = None
    start_skip = CURRENT_SKIP

    # Reply to Forwarded Message Check
    if message.reply_to_message:
        reply = message.reply_to_message
        fwd_chat = getattr(reply, "forward_from_chat", None) or getattr(reply, "sender_chat", None)
        
        if not fwd_chat:
            return await message.reply_text("⚠️ Jis message ko reply kiya hai, wo channel se forwarded message hona chahiye!")

        chat_target = fwd_chat.id
        start_skip = reply.forward_from_message_id or 0
        CURRENT_SKIP = start_skip

    elif len(message.command) > 1:
        raw_target = message.command[1].strip()
        try:
            chat_target = int(raw_target)
        except ValueError:
            chat_target = raw_target
    else:
        return await message.reply_text(
            "⚠️ **Index Kaise Karein:**\n\n"
            "1. Channel se message forward karke reply karein: `/index`\n"
            "2. Direct channel likhein: `/index @channel_username`"
        )

    try:
        chat = await client.get_chat(chat_target)
    except Exception as e:
        return await message.reply_text(
            f"❌ **Channel Access Error:** `{e}`\n\n💡 *Check karein bot channel me Admin hai ya nahi.*"
        )

    INDEX_RUNNING = True
    status_msg = await message.reply_text(
        f"🚀 **Indexing Started:** `{chat.title}`\n\n"
        f"🔘 **Starting From Msg ID:** `{start_skip}`\n"
        f"⏳ Processing files..."
    )

    total_files = 0
    added_files = 0
    skipped_files = 0
    current_msg_id = start_skip

    try:
        async for msg in client.get_chat_history(chat.id, offset_id=start_skip, reverse=True):
            if not INDEX_RUNNING:
                await message.reply_text(f"🛑 **Indexing Stopped!**\n\n📌 Resume Point: `/setskip {current_msg_id}`")
                break

            current_msg_id = msg.id
            CURRENT_SKIP = msg.id

            media = msg.document or msg.video or msg.audio
            if media:
                total_files += 1
                file_name = getattr(media, "file_name", None) or msg.caption or "Unknown"

                is_saved = await db.save_file(
                    file_id=media.file_id,
                    file_name=file_name,
                    file_size=media.file_size,
                    caption=msg.caption or ""
                )

                if is_saved:
                    added_files += 1
                else:
                    skipped_files += 1

                if total_files % 15 == 0:
                    try:
                        await status_msg.edit_text(
                            f"📊 **Indexing In Progress...**\n\n"
                            f"📢 **Channel:** `{chat.title}`\n"
                            f"🔢 **Current Msg ID:** `{current_msg_id}`\n\n"
                            f"✅ **Added Files:** `{added_files}`\n"
                            f"⏭️ **Skipped (Old):** `{skipped_files}`\n"
                            f"📁 **Total Scanned:** `{total_files}`\n\n"
                            f"🛑 *Stop karne ke liye `/cancel` likhein.*"
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(0.3)

        if INDEX_RUNNING:
            await status_msg.edit_text(
                f"🎉 **Indexing Completed!**\n\n"
                f"📢 **Channel:** `{chat.title}`\n"
                f"✅ **Total Added:** `{added_files}`\n"
                f"⏭️ **Total Skipped:** `{skipped_files}`\n"
                f"📁 **Total Scanned:** `{total_files}`\n"
                f"🔢 **Last Message ID:** `{current_msg_id}`"
            )

    except Exception as e:
        await message.reply_text(f"⚠️ **Error Occurred:** `{e}`\n\n💡 Resume: `/setskip {current_msg_id}` fir `/index`")
    finally:
        INDEX_RUNNING = False

# --- SCREENSHOT REPLIES: GROUP WELCOME & ADDED EVENTS ---
@bot.on_message(filters.group & filters.new_chat_members)
async def group_welcome_handler(client: Client, message: Message):
    for member in message.new_chat_members:
        welcome_user_text = ui.get_user_welcome_text(member.first_name, message.chat.title)
        await message.reply_text(
            text=welcome_user_text,
            reply_to_message_id=message.id
        )

        if member.id == client.me.id:
            welcome_text = ui.get_group_welcome_text(message.chat.title)
            welcome_buttons = ui.get_group_welcome_buttons(client.me.username)
            await message.reply_text(
                text=welcome_text,
                reply_markup=welcome_buttons,
                reply_to_message_id=message.id
            )

# --- ADMIN COMMANDS: BAN & UNBAN ---
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

# --- ADMIN COMMANDS: DELETE & DELETEFILES ---
@bot.on_message(filters.command("delete"))
async def delete_single_cmd(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if message.reply_to_message:
        target_msg = message.reply_to_message
        media = target_msg.document or target_msg.video or target_msg.audio
        if not media:
            return await message.reply_text("⚠️ Reply kiye gaye message me koi media nahi hai.")
        deleted = await db.delete_single_file(media.file_id)
        if deleted:
            return await message.reply_text("🗑️ File database se delete kar di gayi hai.")
        return await message.reply_text("⚠️ File database me nahi mili.")

    if len(message.command) > 1:
        name_query = message.text.split(None, 1)[1].strip()
        count = await db.delete_files_by_name(name_query)
        return await message.reply_text(f"🗑️ `{name_query}` ki **{count} files** delete kar di gayi hain.")

    await message.reply_text("⚠️ Usage: File ko reply karke `/delete` ya `/delete Movie_Name` likhein.")

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

# --- START COMMAND (BOT PRIVATE CHAT) ---
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    first_name = message.from_user.first_name if message.from_user else "User"

    if await db.is_user_banned(user_id):
        return await message.reply_text("⛔ **Aapko bot se ban kiya gaya hai.**")

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

    # Group Deep Link File Delivery (4 min delete -> NO WARNING)
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
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "help", "ban", "unban", "delete", "deletefiles", "deleteall", "delall", "index", "setskip", "cancel", "stats"]))
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

    search_msg = await message.reply_text(
        text=caption_text, 
        reply_markup=keyboard,
        reply_to_message_id=message.id
    )

    asyncio.create_task(auto_delete_and_warn(client, chat_id, search_msg.id, first_name, user_id, delay=270))

# --- CALLBACK ROUTER ---
@bot.on_callback_query()
async def callback_router(client: Client, query: CallbackQuery):
    data = query.data
    first_name = query.from_user.first_name or "User"

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
