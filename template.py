import math
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

def humanbytes(size: int) -> str:
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

def format_btn_name(file_name: str, file_size: int) -> str:
    size_str = humanbytes(file_size)
    clean_title = file_name.replace("_", " ").replace(".", " ")
    return f"{size_str} • {clean_title}"

def get_search_caption(first_name: str, query: str) -> str:
    return (
        f"Hey **{first_name}** 👋\n\n"
        "⭕️Rotate your 🔄 phone to see files' full name...........................................⭕️\n\n"
        f"***Title : {query}***\n"
        "***Your Files is Ready Now***"
    )

def build_pagination_keyboard(files: list, query_id: str, page: int, total_pages: int, query_title: str, bot_username: str) -> InlineKeyboardMarkup:
    buttons = []
    
    # 1. Header Button showing Title
    buttons.append([InlineKeyboardButton(f"🎬 {query_title[:28]} 🎬", callback_data="header_click")])
    
    # 2. File list buttons as Deep-link URLs (Taaki tap karte hi niche scroll ho)
    for f in files:
        file_db_id = str(f["_id"])
        btn_text = format_btn_name(f["file_name"], f["file_size"])
        # URL link triggers Telegram auto-scroll
        buttons.append([InlineKeyboardButton(btn_text, url=f"https://t.me/{bot_username}?start=file_{file_db_id}")])
    
    # 3. Bottom Pagination Buttons
    bottom_row = []
    if total_pages <= 1:
        bottom_row.append(InlineKeyboardButton("■ Pages", callback_data="pages_click"))
        bottom_row.append(InlineKeyboardButton("1/1", callback_data="pages_click"))
    else:
        # Previous button
        if page > 1:
            bottom_row.append(InlineKeyboardButton("⏮ Previous", callback_data=f"page_{query_id}_{page-1}"))
        else:
            bottom_row.append(InlineKeyboardButton("■ Pages", callback_data="pages_click"))
        
        # Center Page counter button
        bottom_row.append(InlineKeyboardButton(f"{page} / {total_pages}", callback_data="pages_click"))
        
        # Next button
        if page < total_pages:
            bottom_row.append(InlineKeyboardButton("Next ⏭", callback_data=f"page_{query_id}_{page+1}"))
            
    buttons.append(bottom_row)
    return InlineKeyboardMarkup(buttons)
