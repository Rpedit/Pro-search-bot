import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import UserNotParticipant

import config
from database import db
from template import START_TXT, ABOUT_TXT, FSUB_TXT, FILE_CAPTION_TXT, get_readable_size

bot = Client(
    "auto_filter_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Helper: Shortener function
async def get_shortlink(url):
    if not config.SHORTENER_URL or not config.SHORTENER_API:
        return url
    api_url = f"https://{config.SHORTENER_URL}/api?api={config.SHORTENER_API}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as res:
                data = await res.json()
                if data.get("status") == "success" or "shortenedUrl" in data:
                    return data.get("shortenedUrl", url)
    except Exception as e:
        print(f"Shortener error: {e}")
    return url

# Helper: Force Subscription Check
async def check_fsub(client: Client, user_id: int):
    if not config.FSUB_CHANNEL:
        return True
    try:
        user = await client.get_chat_member(config.FSUB_CHANNEL, user_id)
        if user.status in ["kicked", "left"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

# Channel Indexer: Auto save media posted in DB Channel
@bot.on_message(filters.chat(config.DB_CHANNEL) & (filters.document | filters.video | filters.audio))
async def auto_index_media(client: Client, message: Message):
    media = getattr(message, message.media.value, None)
    if media:
        saved = await db.save_file(media, caption=message.caption or "")
        if saved:
            print(f"[INDEXED] -> {getattr(media, 'file_name', 'Unnamed')}")

# /start command handler
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check force sub
    if not await check_fsub(client, user_id):
        invite_link = await client.export_chat_invite_link(config.FSUB_CHANNEL) if isinstance(config.FSUB_CHANNEL, int) else f"https://t.me/{config.FSUB_CHANNEL}"
        btn = [
            [InlineKeyboardButton("📢 Join Updates Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start={message.command[1] if len(message.command) > 1 else ''}")]
        ]
        return await message.reply_text(FSUB_TXT, reply_markup=InlineKeyboardMarkup(btn))

    # If deep link (file delivery)
    if len(message.command) > 1:
        file_id = message.command[1]
        file_data = await db.get_file(file_id)
        if file_data:
            _, file_name, file_size, caption = file_data
            caption_text = FILE_CAPTION_TXT.format(
                file_name=file_name,
                file_size=get_readable_size(file_size)
            )
            return await client.send_cached_media(
                chat_id=message.chat.id,
                file_id=file_id,
                caption=caption_text
            )
        else:
            return await message.reply_text("❌ Yeh file database me exist nahi karti ya delete ho chuki hai.")

    buttons = [
        [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")],
        [InlineKeyboardButton("🔍 Search Here", switch_inline_query_current_chat="")]
    ]
    await message.reply_text(
        START_TXT.format(mention=message.from_user.mention),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# /stats command (Admin Only)
@bot.on_message(filters.command("stats") & filters.user(config.ADMINS))
async def stats_handler(client: Client, message: Message):
    total = await db.total_files()
    await message.reply_text(f"📊 **Database Stats:**\n\n📁 **Total Indexed Files:** `{total}`")

# Auto Filter Text Search Handler
@bot.on_message(filters.text & filters.private & ~filters.command(["start", "stats"]))
async def filter_search(client: Client, message: Message):
    user_id = message.from_user.id
    query = message.text.strip()

    if not await check_fsub(client, user_id):
        invite_link = await client.export_chat_invite_link(config.FSUB_CHANNEL) if isinstance(config.FSUB_CHANNEL, int) else f"https://t.me/{config.FSUB_CHANNEL}"
        btn = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text(FSUB_TXT, reply_markup=InlineKeyboardMarkup(btn))

    files = await db.search_files(query, limit=10, offset=0)
    if not files:
        return await message.reply_text("❌ **Koi file nahi mili!** Spelling check karke dobara search karein.")

    buttons = []
    for f in files:
        f_id, f_name, f_size = f[0], f[1], f[2]
        size_str = get_readable_size(f_size)
        btn_text = f"[{size_str}] {f_name}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"getfile_{f_id}")])

    # Next page navigation button if 10 results returned
    if len(files) == 10:
        buttons.append([InlineKeyboardButton("Next Page ➡️", callback_data=f"next_{query}_10")])

    await message.reply_text(
        f"🔍 Results for: **{query}**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Callback Queries Handler (Pagination, File Delivery & Details)
@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "about_bot":
        return await query.message.edit_text(
            ABOUT_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_home")]])
        )

    elif data == "back_home":
        buttons = [
            [InlineKeyboardButton("ℹ️ About", callback_data="about_bot")],
            [InlineKeyboardButton("🔍 Search Here", switch_inline_query_current_chat="")]
        ]
        return await query.message.edit_text(
            START_TXT.format(mention=query.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("getfile_"):
        file_id = data.split("_", 1)[1]
        file_data = await db.get_file(file_id)
        if not file_data:
            return await query.answer("File exist nahi karti!", show_alert=True)

        _, file_name, file_size, _ = file_data
        caption_text = FILE_CAPTION_TXT.format(
            file_name=file_name,
            file_size=get_readable_size(file_size)
        )
        await client.send_cached_media(
            chat_id=query.message.chat.id,
            file_id=file_id,
            caption=caption_text
        )
        await query.answer()

    elif data.startswith("next_"):
        _, search_term, offset = data.split("_", 2)
        offset = int(offset)
        files = await db.search_files(search_term, limit=10, offset=offset)

        if not files:
            return await query.answer("Aur files available nahi hain!", show_alert=True)

        buttons = []
        for f in files:
            f_id, f_name, f_size = f[0], f[1], f[2]
            size_str = get_readable_size(f_size)
            buttons.append([InlineKeyboardButton(f"[{size_str}] {f_name}", callback_data=f"getfile_{f_id}")])

        nav = []
        if offset >= 10:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"next_{search_term}_{offset-10}"))
        if len(files) == 10:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"next_{search_term}_{offset+10}"))

        if nav:
            buttons.append(nav)

        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()

async def main():
    await db.connect()
    await bot.start()
    print("🚀 Auto Filter Bot Started Successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
