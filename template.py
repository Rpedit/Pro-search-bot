# =========================================================
# FILE NAME: template.py
# =========================================================

# --- IMPORTS & LIBRARIES ---
import math   # Mathematical calculations ke liye (e.g., file sizes/pagination)
import re     # Regular expressions: filename se dots (.) aur underscores (_) hatane ke liye
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # Telegram buttons banane ke liye

# /start command par aane wali welcome photo ka direct URL
START_PIC = "https://graph.org/file/246a70cb4387b59cceb15-9e968f8602a6acb36c.jpg"


# --- WELCOME & GUIDE MESSAGES ---

# /start command bhejne par user ko aane wala greeting text
def get_start_text(first_name: str) -> str:
    return (
        f"Hey 👋 **{first_name}**🤩\n\n"
        "🍿 **WELCOME TO THE WORLD'S COOLEST SEARCH ENGINE!**\n\n"
        "Here You Can Request Movie's, Just Sent Movie OR WebSeries Name With Proper **Google** Spelling..!!"
    )

# /start message ke neeche aane wale Search Guide aur Share buttons
def get_start_buttons(bot_username: str) -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=Check%20out%20this%20awesome%20Movie%20Search%20Bot!"
    buttons = [
        [InlineKeyboardButton("🔍 SEARCH MOVIES OR SERIES 🔍", callback_data="btn_search_guide")],
        [InlineKeyboardButton("📩 SHARE Now 📩", url=share_url)]
    ]
    return InlineKeyboardMarkup(buttons)

# Jab koi naya member ya bot group join karta hai tab welcome text (Mention Link ke sath)
def get_user_welcome_text(user_first_name: str, user_id: int, group_title: str) -> str:
    user_mention = f"[{user_first_name}](tg://user?id={user_id})"
    return (
        f"**Hey ❤️ {user_mention} ,**\n"
        f"**Welcome to {group_title}.../**"
    )

# Jab bot ko kisi naye group me add kiya jata hai tab admin mangne ka text
def get_group_welcome_text(group_title: str) -> str:
    return (
        f"**Thankyou For Adding Me In**\n"
        f"**{group_title} ❣️**\n\n"
        "›› Don't Forget Make Admin 🙃\n"
        "›› Is Any Doubts About Using\n"
        "Me Click Below Button..⚡️⚡️."
    )

# Group me add hone ke baad aane wale Help/Tutorial buttons
def get_group_welcome_buttons(bot_username: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("ℹ️ Help", url=f"https://t.me/{bot_username}?start=help"),
            InlineKeyboardButton("🧑‍🏫Tutorial", url=f"https://t.me/{bot_username}?start=help")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# Search kaise karein uska format/example samjhane wala popup text
def get_search_guide_text() -> str:
    return (
        "📨 **SEND MOVIE OR SERIES NAME AND YEAR AS PER GOOGLE SPELLING..!!** 👍\n\n"
        "⚠️ **EXAMPLE FOR MOVIE** 👇\n\n"
        "👉 **Jailer**\n"
        "👉 **Jailer 2023**\n\n"
        "⚠️ **EXAMPLE FOR WEBSERIES** 👇\n\n"
        "👉 **Stranger Things**\n"
        "👉 **Stranger Things S02 E04**\n\n"
        "⚠️ **DON'T ADD EMOJIS AND SYMBOLS IN MOVIE NAME, USE LETTERS ONLY..!!** ❌"
    )

# Database me movie/file na milne par warning text
def get_no_results_text() -> str:
    return (
        "●**I could not find the file you requested** 😕\n\n"
        "● **Is the movie you asked about released OTT..?**\n\n"
        "● __Pay attention to the following...__\n\n"
        "● **Ask for correct spelling.**\n\n"
        "● **Do not ask for movies that are not released on OTT platforms.**\n\n"
        "● **Also ask [movie name, language] like this...**"
    )

# Force-Subscribe (FSUB) verification channel join karne ke buttons
def get_fsub_buttons(invite_link: str, bot_username: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_username}?start=start")]
    ]
    return InlineKeyboardMarkup(buttons)


# --- FORMATTING & UTILITIES ---

# File size (bytes) ko readable format (KB, MB, GB) me convert karne ke liye
def humanbytes(size: int) -> str:
    if not size:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"

# File button par display hone wala title format: "1.4 GB • Movie Name"
def format_btn_name(file_name: str, file_size: int) -> str:
    size_str = humanbytes(file_size)
    clean_title = file_name.replace("_", " ").replace(".", " ")
    return f"{size_str} • {clean_title}"

# Search results ke sath aane wala main caption
def get_search_caption(first_name: str, query: str) -> str:
    return (
        f"Hey **{first_name}** 👋\n\n"
        "⭕️Rotate your 🔄 phone to see files' full name...........................................⭕️\n\n"
        f"***Title : {query}***\n"
        "***Your Files is Ready Now***"
    )

# File bhejne ke waqt caption jisme auto-delete warning hoti hai
def get_file_caption(raw_file_name: str) -> str:
    clean_name = re.sub(r"[\._]", " ", raw_file_name).strip()
    return (
        f"**{clean_name}**\n\n"
        "⚠️❌👉This file automatically ❗ delete after 4 minutes ❗ so please forward in another chat👉❌"
    )

# Auto-delete timer complete hone ke baad delete confirmation message
def get_deleted_alert_text(first_name: str, user_id: int) -> str:
    user_mention = f"[{first_name}](tg://user?id={user_id})"
    return (
        f"Hey {user_mention},\n\n"
        "**Your Request Has Been Deleted👍🏻**\n"
        "*(Due To Avoid Copyrights Issue😌)*\n\n"
        "**IF YOU WANT THAT FILE, REQUEST AGAIN ❤️**"
    )


# --- SEARCH RESULT PAGINATION KEYBOARD ---

# Search results ke buttons aur Next/Previous pages create karne ka logic
def build_pagination_keyboard(files: list, query_id: str, page: int, total_pages: int, query_title: str, bot_username: str) -> InlineKeyboardMarkup:
    buttons = []
    
    # Sabse upar Movie Title ka header button
    buttons.append([InlineKeyboardButton(f"🎬 {query_title[:28]} 🎬", callback_data="header_click")])
    
    # Har matching file ka clickable Deep-Link button (jo PM me file bhejta hai)
    for f in files:
        file_db_id = str(f["_id"])
        btn_text = format_btn_name(f["file_name"], f["file_size"])
        buttons.append([InlineKeyboardButton(btn_text, url=f"https://t.me/{bot_username}?start=file_{file_db_id}")])
    
    # Page Navigation Row (Previous / Current Page / Next Buttons)
    bottom_row = []
    if total_pages <= 1:
        bottom_row.append(InlineKeyboardButton("■ Pages", callback_data="pages_click"))
        bottom_row.append(InlineKeyboardButton("1/1", callback_data="pages_click"))
    else:
        # Pichle page par jane ka button
        if page > 1:
            bottom_row.append(InlineKeyboardButton("⏮ Previous", callback_data=f"page_{query_id}_{page-1}"))
        else:
            bottom_row.append(InlineKeyboardButton("■ Pages", callback_data="pages_click"))
        
        # Current page number (e.g. 1 / 5)
        bottom_row.append(InlineKeyboardButton(f"{page} / {total_pages}", callback_data="pages_click"))
        
        # Agle page par jane ka button
        if page < total_pages:
            bottom_row.append(InlineKeyboardButton("Next ⏭", callback_data=f"page_{query_id}_{page+1}"))
            
    buttons.append(bottom_row)
    return InlineKeyboardMarkup(buttons)
