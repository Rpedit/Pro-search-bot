import re
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

START_PIC = "https://graph.org/file/246a70cb4387b59cceb15-9e968f8602a6acb36c.jpg"

def get_start_text(first_name: str) -> str:
    return (
        f"Hey 👋 **{first_name}**🤩\n\n"
        "🍿 **WELCOME TO THE WORLD'S COOLEST SEARCH ENGINE!**\n\n"
        "Here You Can Request Movie's, Just Sent Movie OR WebSeries Name With Proper **Google** Spelling..!!"
    )

def get_start_buttons(bot_username: str) -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=Check%20out%20this%20awesome%20Movie%20Search%20Bot!"
    buttons = [
        [InlineKeyboardButton("🔍 SEARCH MOVIES OR SERIES 🔍", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📩 SHARE Now 📩", url=share_url)]
    ]
    return InlineKeyboardMarkup(buttons)

def get_fsub_buttons(invite_link: str, bot_username: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_username}?start=start")]
    ]
    return InlineKeyboardMarkup(buttons)

def format_file_title(name: str) -> str:
    clean = re.sub(r"[\._]", " ", name)
    tag = "📁"
    name_lower = name.lower()
    if "4k" in name_lower or "2160p" in name_lower:
        tag = "🌟 [4K]"
    elif "1080p" in name_lower:
        tag = "⚡ [1080p]"
    elif "720p" in name_lower:
        tag = "🎬 [720p]"
    elif "480p" in name_lower:
        tag = "📱 [480p]"
    
    display_title = clean[:28] + "..." if len(clean) > 28 else clean
    return f"{tag} {display_title}"

def humanbytes(size: int) -> str:
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"
