# =========================================================
# FILE NAME: broadcast.py
# =========================================================

import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    FloodWait, 
    InputUserDeactivated, 
    UserIsBlocked, 
    PeerIdInvalid
)

from config import ADMINS
import database as db

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# Broadcast Command Handler
async def handle_broadcast(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if not message.reply_to_message:
        return await message.reply_text("⚠️ **Usage:** Kisi message/photo/video ko reply karke `/broadcast` likhein.")

    broadcast_msg = message.reply_to_message
    users = await db.get_all_users()

    if not users:
        return await message.reply_text("⚠️ Database me koi active users nahi mile.")

    total_users = len(users)
    status_msg = await message.reply_text(f"🚀 **Broadcast Shuru Ho Raha Hai...**\n\n👥 Total Users: `{total_users}`")

    success = 0
    blocked = 0
    deleted = 0
    failed = 0
    start_time = time.time()

    for idx, user_id in enumerate(users, start=1):
        try:
            await broadcast_msg.copy(chat_id=user_id)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await broadcast_msg.copy(chat_id=user_id)
                success += 1
            except Exception:
                failed += 1
        except UserIsBlocked:
            blocked += 1
            await db.ban_user(user_id)
        except InputUserDeactivated:
            deleted += 1
            await db.ban_user(user_id)
        except PeerIdInvalid:
            failed += 1
        except Exception:
            failed += 1

        # Har 20 users ke baad live progress status update hoga
        if idx % 20 == 0 or idx == total_users:
            percent = int((idx / total_users) * 100)
            filled = int(percent / 10)
            bar = "🟩" * filled + "⬜" * (10 - filled)
            try:
                await status_msg.edit_text(
                    f"📢 **Broadcast In Progress...**\n\n"
                    f"[{bar}] **{percent}%**\n\n"
                    f"👥 **Processed:** `{idx}/{total_users}`\n"
                    f"✅ **Sent:** `{success}`\n"
                    f"🚫 **Blocked/Deleted:** `{blocked + deleted}`\n"
                    f"⚠️ **Failed:** `{failed}`"
                )
            except Exception:
                pass
        
        await asyncio.sleep(0.05)  # Telegram API flood avoid karne ke liye

    time_taken = round(time.time() - start_time, 2)
    await status_msg.edit_text(
        f"✅ **Broadcast Successfully Completed!**\n\n"
        f"⏱️ **Time Taken:** `{time_taken}s`\n"
        f"👥 **Total Target:** `{total_users}`\n"
        f"🎉 **Sent Successfully:** `{success}`\n"
        f"🚫 **Blocked Users:** `{blocked}`\n"
        f"🗑️ **Deleted Accounts:** `{deleted}`\n"
        f"⚠️ **Failed:** `{failed}`"
    )
