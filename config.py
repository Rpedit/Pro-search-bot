import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")

# Channels & Admins
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "0"))
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", "").replace("@", "").strip()
ADMINS_RAW = os.getenv("ADMINS", "")
ADMINS = [int(x) for x in ADMINS_RAW.split() if x.strip().lstrip("-").isdigit()]

# Shortener Settings (Optional)
SHORTENER_API = os.getenv("SHORTENER_API", "").strip()
SHORTENER_URL = os.getenv("SHORTENER_URL", "").strip()
