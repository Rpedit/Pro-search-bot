# =========================================================
# FILE NAME: template.py
# =========================================================

import re
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

START_PIC = "https://graph.org/file/246a70cb4387b59cceb15-9e968f8602a6acb36c.jpg"

def get_start_text(first_name: str) -> str:
    return (
        f"Hey 👋 **{first_name}** 🤩\n\n"
        "🍿 **WELCOME TO THE WORLD'S COOLEST SEARCH ENGINE!**\n\n"
        "Here You Can Request Movie's, Just Sent Movie OR WebSeries Name With Proper **Google** Spelling..!!"
    )

def get_start_buttons(bot_username: str) -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=Check%20out%20this%20awesome%20Movie%20Search%20Bot!"
    buttons = [
        [InlineKeyboardButton("🔍 SEARCH MOVIES OR SERIES 🔍", callback_data="btn_search_guide")],
        [InlineKeyboardButton("📩 SHARE Now 📩", url=share_url)]
    ]
    return InlineKeyboardMarkup(buttons)

def get_user_welcome_text(user_first_name: str, user_id: int, group_title: str) -> str:
    user_mention = f"[{user_first_name}](tg://user?id={user_id})"
    return f"**Hey ❤️ {user_mention} ,**\n**Welcome to {group_title}.../**"

def get_group_welcome_text(group_title: str) -> str:
    return (
        f"**Thankyou For Adding Me In**\n"
        f"**{group_title} ❣️**\n\n"
        "›› Don't Forget Make Admin 🙃\n"
        "›› Is Any Doubts About Using\n"
        "Me Click Below Button..⚡️⚡️."
    )

def get_group_welcome_buttons(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ℹ️ Help", url=f"https://t.me/{bot_username}?start=help"),
            InlineKeyboardButton("🧑‍🏫 Tutorial", url=f"https://t.me/{bot_username}?start=help")
        ]
    ])

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

def get_no_results_text() -> str:
    return (
        "● **I could not find the file you requested** 😕\n\n"
        "● **Is the movie you asked about released OTT..?**\n\n"
        "● __Pay attention to the following...__\n\n"
        "● **Ask for correct spelling.**\n\n"
        "● **Do not ask for movies that are not released on OTT platforms.**\n\n"
        "● **Also ask [movie name, language] like this...**"
    )

def get_fsub_buttons(invite_link: str, bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
        [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot_username}?start=start")]
    ])

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
    clean = re.sub(r"[\._+@\[\]\(\)\-]", " ", file_name).strip()
    words = []
    for w in clean.split():
        if re.match(r"^(1080p|720p|480p|2160p|4k|web|dl|web-dl|mkv|mp4|esub|hin|kor|eng|tam|tel|kan|mal|dual|uncut|org|hq|hdr|x264|x265|hevc|lo)$", w, re.I):
            if w.lower() == "x265":
                words.append("x265")
            elif w.lower() == "x264":
                words.append("x264")
            elif w.lower() == "esub":
                words.append("ESub")
            elif w.lower() == "lo":
                words.append("lo")
            else:
                words.append(w.upper())
        elif re.match(r"^(s\d{1,2}|e\d{1,2}|ep\d{1,2}|s\d{1,2}e\d{1,2}|s\d{1,2}ep\d{1,2})$", w, re.I):
            words.append(w.upper())
        else:
            words.append(w.capitalize())
            
    clean_title = " ".join(words)
    return f"{size_str} ● {clean_title}"

def get_search_caption(first_name: str, user_id: int, query: str) -> str:
    user_mention = f"[{first_name}](tg://user?id={user_id})"
    return (
        f"Hey __{user_mention}__ 🖐🏻\n\n"
        "⭕️Rotate your 🔄 phone to see files'\n"
        "full name...........................................⭕️\n\n"
        f"***Title : {query.title()}***\n"
        "***Your Files is Ready Now***"
    )

def get_file_caption(raw_file_name: str) -> str:
    clean = re.sub(r"[\._+@\[\]\(\)\-]", " ", raw_file_name).strip()
    words = []
    for w in clean.split():
        if re.match(r"^(1080p|720p|480p|2160p|4k|web|dl|mkv|mp4|esub|hin|kor|eng|tam|tel|kan|mal|uncut|org|hq|hdr)$", w, re.I):
            words.append(w.upper() if w.lower() not in ["uncut", "mkv"] else ("UnCut" if w.lower() == "uncut" else "mkv"))
        else:
            words.append(w.capitalize())
    clean_name = " ".join(words)
    return (
        f"**{clean_name}**\n\n"
        "**⚠️❌👉This file automatically ❗**\n"
        "**delete after 1 minute ❗ so please**\n"
        "**forward in another chat👉❌**"
    )

def get_deleted_alert_text(first_name: str, user_id: int) -> str:
    user_mention = f"[{first_name}](tg://user?id={user_id})"
    return (
        f"Hey __{user_mention}__ ,\n\n"
        "**Your Request Has Been Deleted👍🏻**\n"
        "*(Due To Avoid Copyrights Issue😌)*\n\n"
        "**If You Want That File, REQUEST AGAIN**\n"
        "❤️"
    )

def build_pagination_keyboard(files: list, query_id: str, page: int, total_pages: int, query_title: str, bot_username: str) -> InlineKeyboardMarkup:
    buttons = []
    
    # 1. Top Title Header Row
    formatted_header = query_title.title()[:28]
    buttons.append([InlineKeyboardButton(f"🎬 {formatted_header} 🎬", callback_data="header_click")])
    
    # 2. File Buttons
    for f in files:
        file_db_id = str(f["_id"])
        btn_text = format_btn_name(f["file_name"], f["file_size"])
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"getfile_{file_db_id}")])
    
    # 3. Navigation Bar
    if total_pages <= 1:
        buttons.append([
            InlineKeyboardButton("■ Pages", callback_data="pages_click"),
            InlineKeyboardButton("1/1", callback_data="pages_click")
        ])
    else:
        if page == 1:
            buttons.append([
                InlineKeyboardButton("■ Pages", callback_data="pages_click"),
                InlineKeyboardButton(f"{page}/{total_pages}", callback_data="pages_click"),
                InlineKeyboardButton("Next ⏩", callback_data=f"page_{query_id}_{page+1}")
            ])
        elif page == total_pages:
            buttons.append([
                InlineKeyboardButton("⏪ Previous", callback_data=f"page_{query_id}_{page-1}"),
                InlineKeyboardButton(f"{page} / {total_pages}", callback_data="pages_click")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("⏪ Previous", callback_data=f"page_{query_id}_{page-1}"),
                InlineKeyboardButton(f"{page}/{total_pages}", callback_data="pages_click"),
                InlineKeyboardButton("Next ⏩", callback_data=f"page_{query_id}_{page+1}")
            ])
            
    return InlineKeyboardMarkup(buttons)
