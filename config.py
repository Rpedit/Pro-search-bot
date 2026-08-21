import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "25135658"))
API_HASH = os.getenv("API_HASH", "8bc184fb03aecc4c50f47c7f5aef3177")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")

# Channels & Admins
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1003968479864"))
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", "-1002855667443").replace("@", "https://t.me/HDProSearch").strip()
ADMINS_RAW = os.getenv("ADMINS", "7067885693")
ADMINS = [int(x) for x in ADMINS_RAW.split() if x.strip().lstrip("-").isdigit()]

# Shortener Settings (Optional)
SHORTENER_API = os.getenv("SHORTENER_API", "").strip()
SHORTENER_URL = os.getenv("SHORTENER_URL", "").strip()
