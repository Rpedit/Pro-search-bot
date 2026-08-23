import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import UserNotParticipant

import config
from database import db
from template import (
    START_MSG, 
    ABOUT_MSG, 
    FSUB_MSG, 
    CAPTION_TEMPLATE, 
    format_file_size
)

bot = Client(
    "auto_filter_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Helper: Check Force Subscribe
async def check_user_fsub(client: Client, user_id: int):
    if not config.FSUB_CHANNEL:
        return True
    try:
        member = await client.get_chat_member(config.FSUB_CHANNEL, user_id)
        if member.status in ["kicked", "left"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

# Channel Auto-Indexer Handler
@bot.on_message(filters.chat(config.DB_CHANNEL) & (filters.document | filters.video | filters.audio))
async def handle_channel_media(client: Client, message: Message):
    media = getattr(message, message.media.value, None)
    if media:
        caption = message.caption or ""
        await db.save_file(media, caption=caption)

# /start Handler
@bot.on_message(filters.command("start") & filters.private)
async def handle_start(client: Client, message: Message):
    user_id = message.from_user.id
    
    # 1. Force-Sub Check
    is_subscribed = await check_user_fsub(client, user_id)
    if not is_subscribed:
        invite_link = await client.export_chat_invite_link(config.FSUB_CHANNEL) if isinstance(config.FSUB_CHANNEL, int) else f"https://t.me/{config.FSUB_CHANNEL}"
        btn = [
            [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start={message.command[1] if len(message.command) > 1 else ''}")]
        ]
        return await message.reply_text(FSUB_MSG, reply_markup=InlineKeyboardMarkup(btn))

    # 2. Deep Link Direct File Send
    if len(message.command) > 1 and message.command[1].isdigit():
        db_id = int(message.command[1])
        file_info = await db.get_file_by_id(db_id)
        if file_info:
            caption_text = CAPTION_TEMPLATE.format(
                title=file_info["file_name"],
                size=format_file_size(file_info["file_size"])
            )
            return await client.send_cached_media(
                chat_id=message.chat.id,
                file_id=file_info["file_id"],
                caption=caption_text
            )
        else:
            return await message.reply_text("❌ File database me nahi mili.")

    # 3. Default Start Panel
    buttons = [
        [InlineKeyboardButton("ℹ️ About", callback_data="btn_about")]
    ]
    await message.reply_text(
        START_MSG.format(user_mention=message.from_user.mention),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# /stats Admin Command
@bot.on_message(filters.command("stats") & filters.user(config.ADMINS))
async def handle_stats(client: Client, message: Message):
    total = await db.count_all_files()
    await message.reply_text(f"📊 **Database Index Status:**\n\n📁 Total Files: `{total}`")

# Search Handler for Any Text
@bot.on_message(filters.text & filters.private & ~filters.command(["start", "stats"]))
async def handle_search(client: Client, message: Message):
    user_id = message.from_user.id
    search_query = message.text.strip()

    # Sub check
    if not await check_user_fsub(client, user_id):
        invite_link = await client.export_chat_invite_link(config.FSUB_CHANNEL) if isinstance(config.FSUB_CHANNEL, int) else f"https://t.me/{config.FSUB_CHANNEL}"
        btn = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]]
        return await message.reply_text(FSUB_MSG, reply_markup=InlineKeyboardMarkup(btn))

    files = await db.search_files(search_query, limit=10, offset=0)
    if not files:
        return await message.reply_text("❌ **Koi file nahi mili!** Spelling check karke dobara search karein.")

    buttons = []
    for db_id, f_name, f_size in files:
        size_label = format_file_size(f_size)
        display_name = (f_name[:38] + "..") if len(f_name) > 38 else f_name
        button_text = f"[{size_label}] {display_name}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"dl_{db_id}")])

    if len(files) == 10:
        clean_keyword = "".join([c if c.isalnum() else "_" for c in search_query])[:15]
        buttons.append([InlineKeyboardButton("Next ➡️", callback_data=f"page_{clean_keyword}_10")])

    await message.reply_text(
        f"🔍 Results for: **{search_query}**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Callback Query Handler
@bot.on_callback_query()
async def handle_callbacks(client: Client, query: CallbackQuery):
    data = query.data

    if data == "btn_about":
        btn = [[InlineKeyboardButton("⬅️ Back", callback_data="btn_back")]]
        return await query.message.edit_text(ABOUT_MSG, reply_markup=InlineKeyboardMarkup(btn))

    elif data == "btn_back":
        buttons = [[InlineKeyboardButton("ℹ️ About", callback_data="btn_about")]]
        return await query.message.edit_text(
            START_MSG.format(user_mention=query.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("dl_"):
        db_id = data.split("_", 1)[1]
        file_info = await db.get_file_by_id(db_id)
        if not file_info:
            return await query.answer("File nahi mili!", show_alert=True)

        caption_text = CAPTION_TEMPLATE.format(
            title=file_info["file_name"],
            size=format_file_size(file_info["file_size"])
        )
        await client.send_cached_media(
            chat_id=query.message.chat.id,
            file_id=file_info["file_id"],
            caption=caption_text
        )
        await query.answer()

    elif data.startswith("page_"):
        _, keyword, offset = data.split("_", 2)
        offset = int(offset)
        files = await db.search_files(keyword.replace("_", " "), limit=10, offset=offset)

        if not files:
            return await query.answer("Aur files nahi hain!", show_alert=True)

        buttons = []
        for db_id, f_name, f_size in files:
            size_label = format_file_size(f_size)
            display_name = (f_name[:38] + "..") if len(f_name) > 38 else f_name
            buttons.append([InlineKeyboardButton(f"[{size_label}] {display_name}", callback_data=f"dl_{db_id}")])

        nav_row = []
        if offset >= 10:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{keyword}_{offset-10}"))
        if len(files) == 10:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{keyword}_{offset+10}"))

        if nav_row:
            buttons.append(nav_row)

        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()

async def main():
    await db.connect()
    await bot.start()
    print("🚀 HD Pro Search Bot Started Successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
