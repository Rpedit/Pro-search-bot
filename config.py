import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "25135658"))
API_HASH = os.getenv("API_HASH", "8bc184fb03aecc4c50f47c7f5aef3177")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Channels & Admins
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1003968479864"))
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", "-1002855667443").replace("@", "https://t.me/HDProSearch").strip()
ADMINS_RAW = os.getenv("ADMINS", "7067885693")
ADMINS = [int(x) for x in ADMINS_RAW.split() if x.strip().lstrip("-").isdigit()]

# --- DUAL MONGO DATABASE SETTINGS ---
# Database 1 (Primary)
DATABASE_URI_1 = os.getenv("DATABASE_URI_1", os.getenv("MONGO_URI", "mongodb+srv://rpeditz:rpeditz@rpeditz.tzgtpiq.mongodb.net/?retryWrites=true&w=majority&appName=rpeditz"))

# Database 2 (Secondary / Backup)
DATABASE_URI_2 = os.getenv("DATABASE_URI_2", "").strip()

# Switch: 'True' karne par DB2 me save hoga, 'False' par DB1 me
USE_SECOND_DB = os.getenv("USE_SECOND_DB", "False").lower() in ["true", "1"]

# Shortener Settings (Optional)
SHORTENER_API = os.getenv("SHORTENER_API", "").strip()
SHORTENER_URL = os.getenv("SHORTENER_URL", "").strip()
