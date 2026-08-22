# =========================================================
# FILE NAME: broadcast.py
# =========================================================

import time
import secrets
import asyncio
from pyrogram import Client
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from pyrogram.errors import (
    FloodWait, 
    InputUserDeactivated, 
    UserIsBlocked, 
    PeerIdInvalid
)

from config import ADMINS
import database as db

# Broadcast sessions store karne ke liye temporary memory
PENDING_BROADCASTS = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# 1. Broadcast command aane par buttons show karne ka handler
async def handle_broadcast(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("⛔ Sirf Admins ye command use kar sakte hain.")

    if not message.reply_to_message:
        return await message.reply_text("⚠️ **Usage:** Kisi message ko reply karke `/broadcast` likhein.")

    task_id = secrets.token_hex(4)
    PENDING_BROADCASTS[task_id] = {
        "chat_id": message.chat.id,
        "message_id": message.reply_to_message.id
    }

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Normal Send", callback_data=f"bcast_normal_{task_id}"),
            InlineKeyboardButton("📌 Pin & Send", callback_data=f"bcast_pin_{task_id}")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data=f"bcast_cancel_{task_id}")
        ]
    ])

    await message.reply_text(
        "📢 **Broadcast Mode Select Karein:**\n\n"
        "• **Normal Send:** Bina pin kiye message send karega.\n"
        "• **Pin & Send:** Message send karke users ki chat me pin karega.",
        reply_markup=buttons,
        reply_to_message_id=message.reply_to_message.id
    )

# 2. Button click hone par actual broadcast process karne ka handler
async def handle_broadcast_callback(client: Client, query: CallbackQuery):
    data = query.data

    if not is_admin(query.from_user.id):
        return await query.answer("⛔ Access Denied!", show_alert=True)

    if data.startswith("bcast_cancel_"):
        task_id = data.replace("bcast_cancel_", "")
        PENDING_BROADCASTS.pop(task_id, None)
        await query.message.edit_text("❌ **Broadcast cancel kar diya gaya.**")
        return await query.answer("Cancelled")

    should_pin = data.startswith("bcast_pin_")
    task_id = data.replace("bcast_pin_", "") if should_pin else data.replace("bcast_normal_", "")

    bcast_data = PENDING_BROADCASTS.pop(task_id, None)
    if not bcast_data:
        return await query.answer("⚠️ Session Expired! Dubara `/broadcast` likhein.", show_alert=True)

    await query.answer()

    users = await db.get_all_users()
    if not users:
        return await query.message.edit_text("⚠️ Database me koi active users nahi mile.")

    total_users = len(users)
    pin_text = " (With Auto-Pin 📌)" if should_pin else ""
    await query.message.edit_text(f"🚀 **Broadcast Shuru Ho Raha Hai{pin_text}...**\n\n👥 Total Users: `{total_users}`")

    success = 0
    pinned_count = 0
    blocked = 0
    deleted = 0
    failed = 0
    start_time = time.time()

    for idx, user_id in enumerate(users, start=1):
        try:
            sent = await client.copy_message(
                chat_id=user_id,
                from_chat_id=bcast_data["chat_id"],
                message_id=bcast_data["message_id"]
            )
            success += 1
            
            if should_pin and sent:
                try:
                    await client.pin_chat_message(chat_id=user_id, message_id=sent.id, both_sides=True)
                    pinned_count += 1
                except Exception:
                    pass

        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                sent = await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=bcast_data["chat_id"],
                    message_id=bcast_data["message_id"]
                )
                success += 1
                if should_pin and sent:
                    try:
                        await client.pin_chat_message(chat_id=user_id, message_id=sent.id, both_sides=True)
                        pinned_count += 1
                    except Exception:
                        pass
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

        # Har 20 users ke baad progress update
        if idx % 20 == 0 or idx == total_users:
            percent = int((idx / total_users) * 100)
            filled = int(percent / 10)
            bar = "🟩" * filled + "⬜" * (10 - filled)
            try:
                pin_status = f"📌 **Pinned:** `{pinned_count}`\n" if should_pin else ""
                await query.message.edit_text(
                    f"📢 **Broadcast In Progress...**\n\n"
                    f"[{bar}] **{percent}%**\n\n"
                    f"👥 **Processed:** `{idx}/{total_users}`\n"
                    f"✅ **Sent:** `{success}`\n"
                    f"{pin_status}"
                    f"🚫 **Blocked/Deleted:** `{blocked + deleted}`\n"
                    f"⚠️ **Failed:** `{failed}`"
                )
            except Exception:
                pass
        
        await asyncio.sleep(0.05)

    time_taken = round(time.time() - start_time, 2)
    pin_summary = f"📌 **Total Pinned:** `{pinned_count}`\n" if should_pin else ""
    await query.message.edit_text(
        f"✅ **Broadcast Successfully Completed!**\n\n"
        f"⏱️ **Time Taken:** `{time_taken}s`\n"
        f"👥 **Total Target:** `{total_users}`\n"
        f"🎉 **Sent Successfully:** `{success}`\n"
        f"{pin_summary}"
        f"🚫 **Blocked Users:** `{blocked}`\n"
        f"🗑️ **Deleted Accounts:** `{deleted}`\n"
        f"⚠️ **Failed:** `{failed}`"
    )
