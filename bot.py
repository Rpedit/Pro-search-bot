import aiohttp
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
from config import API_ID, API_HASH, BOT_TOKEN, DB_CHANNEL, FSUB_CHANNEL, SHORTENER_API, SHORTENER_URL
import database as db
import template as ui

bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

async def get_shortlink(url: str):
    if not SHORTENER_API or not SHORTENER_URL:
        return url
    api_endpoint = f"https://{SHORTENER_URL}/api?api={SHORTENER_API}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint, timeout=8) as res:
                data = await res.json()
                return data.get("shortenedUrl", url)
    except Exception:
        return url

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

# --- START HANDLER ---
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

    # Deep Link Handler
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        db_id = message.command[1].replace("file_", "")
        file_data = await db.get_file_by_id(db_id)
        if file_data:
            return await client.send_cached_media(
                chat_id=user_id,
                file_id=file_data["file_id"],
                caption=f"🎬 **File:** `{file_data['file_name']}`\n⚡ **Size:** `{ui.humanbytes(file_data['file_size'])}`\n\n🤖 **Bot:** @{client.me.username}"
            )

    caption_text = ui.get_start_text(first_name)
    markup = ui.get_start_buttons(client.me.username)

    try:
        await message.reply_photo(
            photo=ui.START_PIC,
            caption=caption_text,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Photo send failed, sending text fallback: {e}", flush=True)
        await message.reply_text(
            text=caption_text,
            reply_markup=markup
        )

# --- INLINE QUERY HANDLER ---
@bot.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    text = query.query.strip()
    if not text:
        return await query.answer([], switch_pm_text="Movie ya Series ka naam likhein...", switch_pm_parameter="help")

    files = await db.search_files(text, limit=30)
    results = []

    for f in files:
        file_db_id = str(f["_id"])
        size_str = ui.humanbytes(f["file_size"])
        btn = [[InlineKeyboardButton("📥 Get File", url=f"https://t.me/{client.me.username}?start=file_{file_db_id}")]]
        
        results.append(
            InlineQueryResultArticle(
                title=f["file_name"],
                description=f"Size: {size_str}",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎬 **File:** `{f['file_name']}`\n⚡ **Size:** `{size_str}`"
                ),
                reply_markup=InlineKeyboardMarkup(btn)
            )
        )

    await query.answer(results=results, cache_time=5)

# --- AUTO INDEX ---
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

    if message.chat.type.value == "private" and not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        btn = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text("⚠️ Pehle hamara update channel join karein.", reply_markup=InlineKeyboardMarkup(btn))

    query = message.text.strip()
    files = await db.search_files(query, limit=10)

    if not files:
        return await message.reply_text(
            f"❌ **No results found for:** `{query}`\n\n"
            "💡 **Tips:**\n"
            "• Google par spelling verify karein\n"
            "• Year ya season hata kar search karein"
        )

    buttons = []
    for f in files:
        file_db_id = str(f["_id"])
        formatted_title = ui.format_file_title(f["file_name"])
        size_str = ui.humanbytes(f["file_size"])
        btn_text = f"{formatted_title} [{size_str}]"
        
        if SHORTENER_API and SHORTENER_URL:
            deep_link = f"https://t.me/{client.me.username}?start=file_{file_db_id}"
            short_link = await get_shortlink(deep_link)
            buttons.append([InlineKeyboardButton(btn_text, url=short_link)])
        else:
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{file_db_id}")])

    await message.reply_text(
        f"🔍 **Found {len(files)} result(s) for:** `{query}`\n👇 *Click button below to download:*",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- SEND FILE CALLBACK ---
@bot.on_callback_query(filters.regex(r"^send_"))
async def callback_send_file(client: Client, query: CallbackQuery):
    db_id = query.data.split("_")[1]
    file_data = await db.get_file_by_id(db_id)
    if not file_data:
        return await query.answer("❌ File database me nahi mili!", show_alert=True)
        
    await query.answer("Sending file...")
    await client.send_cached_media(
        chat_id=query.from_user.id,
        file_id=file_data["file_id"],
        caption=f"🎬 **File:** `{file_data['file_name']}`\n⚡ **Size:** `{ui.humanbytes(file_data['file_size'])}`\n\n🤖 **Bot:** @{client.me.username}"
    )

async def main():
    await db.init_db()
    await bot.start()
    print(">>> BOT IS ONLINE AND LISTENING <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
