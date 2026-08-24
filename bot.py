import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultCachedDocument
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, BOT_TOKEN, FSUB_CHANNEL, ADMINS
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Main client
app = Client(
    "HDProSearchBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # Force Subscription Check
    if FSUB_CHANNEL:
        try:
            # Handle int or str channel id/username
            if str(FSUB_CHANNEL).startswith("-100") or str(FSUB_CHANNEL).isdigit():
                chat_id = int(FSUB_CHANNEL)
            else:
                chat_id = FSUB_CHANNEL if FSUB_CHANNEL.startswith("@") else f"@{FSUB_CHANNEL}"

            user = await client.get_chat_member(chat_id, message.from_user.id)
            if user.status in [ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
                await message.reply("❌ Aapko channel se ban ya restrict kiya gaya hai!")
                return
        except UserNotParticipant:
            invite_link = f"https://t.me/{str(FSUB_CHANNEL).replace('@', '')}"
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)]
            ])
            await message.reply(
                "👋 **Hello!** Bot ko use karne ke liye pehle hamara update channel join karna zaroori hai.",
                reply_markup=btn
            )
            return
        except Exception as e:
            logger.error(f"FSUB Check Error: {e}")
            # Agar bot khud admin nahi hai ya koi aur issue aaye toh start process continue rahega

    user_name = message.from_user.first_name if message.from_user else "User"
    await message.reply(
        f"👋 Hello **{user_name}**!\n\n"
        "Main **iPapkorn style** Auto-Filter Bot hoon. Mujhe kisi bhi Movie ya Series ka naam bhejo, main aapko turant file dunga! 🚀"
    )

@app.on_message(filters.text & filters.private & ~filters.command(["start", "help"]))
async def auto_filter(client, message):
    query = message.text.strip()
    if len(query) < 2:
        await message.reply("Kripya kam se kam 2 letters likhein search karne ke liye.")
        return

    try:
        files = await db.search_files(query, max_results=10)
        
        if not files:
            await message.reply("❌ Koi bhi file nahi mili! Spelling check karke dobara try karein.")
            return

        text = f"🔍 **Search Results for:** `{query}`\n\n"
        buttons = []
        
        for file in files:
            buttons.append([InlineKeyboardButton(file['file_name'], callback_data=f"file_{file['file_id'][:10]}")])

        await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"Search Error: {e}")
        await message.reply("⚠️ Search karte waqt error aaya. Kripya baad me try karein.")

@app.on_inline_query()
async def inline_search(client, inline_query):
    query = inline_query.query.strip()
    results = []
    
    if query:
        try:
            files = await db.search_files(query, max_results=20)
            for file in files:
                results.append(
                    InlineQueryResultCachedDocument(
                        title=file['file_name'],
                        file_id=file['file_id'],
                        caption=f"📁 **{file['file_name']}**\n\n✨ Shared via HDPro Search Bot",
                    )
                )
        except Exception as e:
            logger.error(f"Inline Search Error: {e}")
            
    await inline_query.answer(results, cache_time=1)
