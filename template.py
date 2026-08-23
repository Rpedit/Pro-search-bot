import math

def get_readable_size(size_bytes):
    if not size_bytes:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

START_TXT = """
👋 **Hello {mention}**,

Welcome to **HD Pro Search Bot**! 🔍

Main channel files ko index karta hoon aur aapke keywords ke hisab se exact file buttons provide karta hoon.
"""

ABOUT_TXT = """
🤖 **Bot Name:** HD Pro Search Bot
⚡ **Framework:** Pyrogram & LibSQL (Turso)
🌐 **Developer:** @RPEDITZ
"""

FSUB_TXT = """
⚠️ **Access Denied!**

Aapko search results ya files lene ke liye pehle hamara **Updates Channel** join karna padega. 

Join karne ke baad niche **Verify / Try Again** button par click karein.
"""

FILE_CAPTION_TXT = """
📁 **File Name:** `{file_name}`
📊 **Size:** `{file_size}`

⚡ *Powered by HD Pro Search*
"""
