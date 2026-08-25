import math
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def humanbytes(size):
    """File size ko readable format (MB, GB) me convert karta hai"""
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def get_search_message(query: str, user_mention: str) -> str:
    """Search message layout banner format"""
    return (
        f"Hey {user_mention} 👋\n\n"
        f"⭕️Rotate your 🔄 phone to see files' full name......................................⭕️\n\n"
        f"**Title : {query}**\n"
        f"__Your Files is Ready Now__"
    )

def build_pagination_keyboard(results: list, query: str, page: int = 1, per_page: int = 8):
    """Screenshot ke design ke according inline buttons layout"""
    total_files = len(results)
    total_pages = math.ceil(total_files / per_page)
    if total_pages == 0:
        total_pages = 1

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_files = results[start_idx:end_idx]

    buttons = []

    # Title Button Header
    buttons.append([InlineKeyboardButton(f"🎬 {query[:28]} 🎬", callback_data="pages_info")])

    # Files List
    for file in page_files:
        size_str = humanbytes(file.get("file_size", 0))
        name_str = file.get("file_name", "File")
        btn_text = f"{size_str} • {name_str}"
        
        # Slicing for Telegram button text limit
        if len(btn_text) > 42:
            btn_text = btn_text[:39] + "..."
            
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"get_{file['file_id']}")])

    # Navigation Footer Row
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"nav_{query}_{page - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("▪️ Pages", callback_data="pages_info"))

    nav_buttons.append(InlineKeyboardButton(f"{page} / {total_pages}", callback_data="pages_info"))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ⏩", callback_data=f"nav_{query}_{page + 1}"))

    buttons.append(nav_buttons)
    return InlineKeyboardMarkup(buttons)
