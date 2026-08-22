import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMINS
import database as db

CURRENT_SKIP = 0
INDEX_RUNNING = False

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# --- SET SKIP COMMAND ---
@Client.on_message(filters.command("setskip") & filters.private)
async def set_skip_handler(client: Client, message: Message):
    global CURRENT_SKIP
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if len(message.command) < 2:
        return await message.reply_text(
            f"⚠️ **Skip Number Enter Karein:**\n👉 `/setskip 2000`\n\n📌 **Current Skip:** `{CURRENT_SKIP}`"
        )

    try:
        CURRENT_SKIP = int(message.command[1])
        await message.reply_text(
            f"✅ **Skip Count Set:** `{CURRENT_SKIP}`\n"
            f"Ab `/index` chalane par ye Msg ID `{CURRENT_SKIP}` se aage fetch karega."
        )
    except ValueError:
        await message.reply_text("⚠️ Sahi numeric number enter karein.")

# --- CANCEL INDEX COMMAND ---
@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_index_handler(client: Client, message: Message):
    global INDEX_RUNNING
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if not INDEX_RUNNING:
        return await message.reply_text("⚠️ Abhi koi indexing process nahi chal raha hai.")

    INDEX_RUNNING = False
    await message.reply_text("🛑 **Stopping Indexing...** Process cancel kiya ja raha hai.")

# --- FORWARD REPLY / BULK CHANNEL INDEX COMMAND ---
@Client.on_message(filters.command("index") & filters.private)
async def bulk_index_handler(client: Client, message: Message):
    global CURRENT_SKIP, INDEX_RUNNING
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if INDEX_RUNNING:
        return await message.reply_text("⚠️ Indexing pehle se chal rahi hai! Rokne ke liye `/cancel` likhein.")

    chat_target = None
    start_skip = CURRENT_SKIP

    # 1. Forward Message Ko Reply Karke Index Karna
    if message.reply_to_message:
        reply = message.reply_to_message
        fwd_chat = reply.forward_from_chat or reply.sender_chat
        
        if not fwd_chat:
            return await message.reply_text("⚠️ Jis message ko reply kiya hai, wo channel se forward kiya hua hona chahiye.")

        chat_target = fwd_chat.id
        start_skip = reply.forward_from_message_id or 0
        CURRENT_SKIP = start_skip

    # 2. Command Ke Sath Username/ID Likh Kar Index Karna -> /index @channel
    elif len(message.command) > 1:
        raw_target = message.command[1].strip()
        try:
            chat_target = int(raw_target)
        except ValueError:
            chat_target = raw_target

    else:
        return await message.reply_text(
            "⚠️ **Kaise use karein:**\n\n"
            "1. Channel se koi bhi message bot ko forward karein aur uspar reply karke likhein: `/index`\n"
            "2. Direct channel likhein: `/index @channel_username`"
        )

    try:
        chat = await client.get_chat(chat_target)
    except Exception as e:
        return await message.reply_text(
            f"❌ **Channel Access Error:** `{e}`\n\n"
            "💡 *Check karein bot us channel me Admin bana hai ya nahi.*"
        )

    INDEX_RUNNING = True
    status_msg = await message.reply_text(
        f"🚀 **Indexing Started:** `{chat.title}`\n\n"
        f"🔘 **Starting Offset ID:** `{start_skip}`\n"
        f"⏳ Processing files..."
    )

    total_files = 0
    added_files = 0
    skipped_files = 0
    current_msg_id = start_skip

    try:
        async for msg in client.get_chat_history(chat.id, offset_id=start_skip, reverse=True):
            if not INDEX_RUNNING:
                await message.reply_text(
                    f"🛑 **Indexing Stopped!**\n\n"
                    f"📌 **Resume point:** `/setskip {current_msg_id}`"
                )
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

                # Har 20 files ke baad update
                if total_files % 20 == 0:
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
                    await asyncio.sleep(0.4)

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
        await message.reply_text(
            f"⚠️ **Error Occurred:** `{e}`\n\n"
            f"💡 Resume point: `/setskip {current_msg_id}`"
        )
    finally:
        INDEX_RUNNING = False
