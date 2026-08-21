import re
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

bot = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# Custom banner image URL
START_PIC = "https://graph.org/file/246a70cb4387b59cceb15-9e968f8602a6acb36c.jpg"

def format_name(name: str):
    clean = re.sub(r"[\._]", " ", name)
    tag = "📁"
    if "4k" in name.lower() or "2160p" in name.lower():
        tag = "🌟 [4K]"
    elif "1080p" in name.lower():
        tag = "⚡ [1080p]"
    elif "720p" in name.lower():
        tag = "🎬 [720p]"
    elif "480p" in name.lower():
        tag = "📱 [480p]"
    
    display_title = clean[:30] + "..." if len(clean) > 30 else clean
    return f"{tag} {display_title}"

def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

async def get_shortlink(url):
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

# --- START COMMAND (CUSTOM UI) ---
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    await db.add_user(user_id)

    # Force-Subscribe check
    if not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        btn = [
            [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start=start")]
        ]
        return await message.reply_photo(
            photo=START_PIC,
            caption="⚠️ **Access Denied!**\n\nPehle hamara update channel join karein, fir **Try Again** par click karein.",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    # Deep Link Check
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        db_id = message.command[1].replace("file_", "")
        file_data = await db.get_file_by_id(db_id)
        if file_data:
            return await client.send_cached_media(
                chat_id=user_id,
                file_id=file_data["file_id"],
                caption=f"🎬 **File Name:** `{file_data['file_name']}`\n⚡ **Size:** `{humanbytes(file_data['file_size'])}`\n\n🤖 **Bot:** @{client.me.username}"
            )

    start_text = (
        f"Hey 👋 **{message.from_user.first_name}**🤩\n\n"
        "🍿 **WELCOME TO THE WORLD'S COOLEST SEARCH ENGINE!**\n\n"
        "Here You Can Request Movie's, Just Sent Movie OR WebSeries Name With Proper Google Spelling..!!"
    )

    share_text = f"Hey! Check out this awesome Movie & Series Search Bot: @{client.me.username}"
    share_url = f"https://t.me/share/url?url={share_text}"

    buttons = [
        [InlineKeyboardButton("🔍 SEARCH MOVIES OR SERIES 🔍", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📩 SHARE Now 📩", url=share_url)]
    ]

    await message.reply_photo(
        photo=START_PIC,
        caption=start_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- INLINE SEARCH SUPPORT ---
@bot.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    text = query.query.strip()
    if not text:
        return await query.answer([], switch_pm_text="Movie ya Series ka naam likhein...", switch_pm_parameter="help")

    files = await db.search_files(text, limit=30)
    results = []

    for f in files:
        file_db_id = str(f["_id"])
        formatted_title = format_name(f["file_name"])
        size_str = humanbytes(f["file_size"])
        
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

# --- NORMAL TEXT SEARCH HANDLER ---
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
            "• Check spelling on Google\n"
            "• Remove year or season details and search only the movie title."
        )

    buttons = []
    for f in files:
        file_db_id = str(f["_id"])
        formatted_title = format_name(f["file_name"])
        size_str = humanbytes(f["file_size"])
        btn_text = f"{formatted_title} [{size_str}]"
        
        if SHORTENER_API and SHORTENER_URL:
            bot_username = client.me.username
            deep_link = f"https://t.me/{bot_username}?start=file_{file_db_id}"
            short_link = await get_shortlink(deep_link)
            buttons.append([InlineKeyboardButton(btn_text, url=short_link)])
        else:
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{file_db_id}")])

    await message.reply_text(
        f"🔍 **Found {len(files)} result(s) for:** `{query}`\n👇 *Click on the button below to get your file:*",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- DIRECT FILE CALLBACK ---
@bot.on_callback_query(filters.regex(r"^send_"))
async def callback_send_file(client: Client, query: CallbackQuery):
    db_id = query.data.split("_")[1]
    file_data = await db.get_file_by_id(db_id)
    if not file_data:
        return await query.answer("❌ File not found in database!", show_alert=True)
        
    await query.answer("Sending file...")
    await client.send_cached_media(
        chat_id=query.from_user.id,
        file_id=file_data["file_id"],
        caption=f"🎬 **File:** `{file_data['file_name']}`\n⚡ **Size:** `{humanbytes(file_data['file_size'])}`\n\n🤖 **Bot:** @{client.me.username}"
    )

async def main():
    await db.init_db()
    await bot.start()
    print(">>> BOT IS ONLINE AND LISTENING <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
