import aiohttp
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
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

async def get_shortlink(url):
    if not SHORTENER_API or not SHORTENER_URL:
        return url
    api_endpoint = f"https://{SHORTENER_URL}/api?api={SHORTENER_API}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint, timeout=10) as res:
                data = await res.json()
                return data.get("shortenedUrl", url)
    except Exception:
        return url

def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

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

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await db.add_user(user_id)

    if not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        btn = [
            [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start=start")]
        ]
        return await message.reply_text(
            "⚠️ **Aapko files lene ke liye pehle hamara channel join karna hoga!**",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    if len(message.command) > 1 and message.command[1].startswith("file_"):
        file_id = message.command[1].replace("file_", "")
        return await client.send_cached_media(chat_id=user_id, file_id=file_id)

    await message.reply_text(
        f"👋 **Namaste {message.from_user.mention}!**\n\n"
        "Mujhe kisi bhi Movie ya Series ka naam bhejo, main aapko file provide kar dunga."
    )

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

@bot.on_message(filters.text & ~filters.command(["start", "help"]))
async def filter_search(client: Client, message: Message):
    user_id = message.from_user.id

    if message.chat.type.value == "private" and not await is_subscribed(client, user_id):
        invite_link = await get_fsub_link(client)
        btn = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text("⚠️ Pehle channel join karein files access karne ke liye.", reply_markup=InlineKeyboardMarkup(btn))

    query = message.text.strip()
    files = await db.search_files(query, limit=10)

    if not files:
        return await message.reply_text("❌ **Koi result nahi mila!**\nSpelling check karein.")

    buttons = []
    for f in files:
        btn_text = f"🎬 {f['file_name'][:28]}... [{humanbytes(f['file_size'])}]"
        if SHORTENER_API and SHORTENER_URL:
            bot_username = client.me.username
            deep_link = f"https://t.me/{bot_username}?start=file_{f['file_id']}"
            short_link = await get_shortlink(deep_link)
            buttons.append([InlineKeyboardButton(btn_text, url=short_link)])
        else:
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{f['file_id']}")])

    await message.reply_text(
        f"🔍 **Found {len(files)} result(s) for:** `{query}`",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@bot.on_callback_query(filters.regex(r"^send_"))
async def callback_send_file(client: Client, query: CallbackQuery):
    file_id = query.data.split("_")[1]
    await query.answer("File bhej raha hu...")
    await client.send_cached_media(chat_id=query.from_user.id, file_id=file_id)

async def main():
    await db.init_db()
    await bot.start()
    print(">>> BOT IS ONLINE AND LISTENING <<<", flush=True)
    await idle()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
