import math

def format_file_size(size_bytes):
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    size_units = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_units[i]}"

START_MSG = """
👋 **Namaste {user_mention}**,

Welcome to **HD Pro Search Bot**! 🔍

Aap yahan direct movie ya file ka naam likh kar search kar sakte hain.
"""

ABOUT_MSG = """
🤖 **Bot:** HD Pro Search
⚡ **Engine:** Pyrogram & Turso LibSQL
👤 **Owner:** @RPEDITZ
"""

FSUB_MSG = """
⚠️ **Channel Join Required!**

Search results access karne ke liye kripya pehle hamara official channel join karein. 

Join karne ke baad niche **🔄 Try Again** par click karein.
"""

CAPTION_TEMPLATE = """
🎬 **Title:** `{title}`
📦 **Size:** `{size}`

⚡ *Powered by HD Pro Search*
"""
