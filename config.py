import os

# --- Telegram API Credentials ---
API_ID = int(os.environ.get("API_ID", "12345678"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

# --- Admins & Indexing Channels ---
ADMINS = [int(admin) for admin in os.environ.get("ADMINS", "123456789").split()]
INDEX_CHANNELS = [int(ch) for ch in os.environ.get("INDEX_CHANNELS", "-1001234567890").split()]

# --- Force Subscribe Settings ---
FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", "-1001234567890"))
FORCE_SUB_INVITE = os.environ.get("FORCE_SUB_INVITE", "https://t.me/YourChannelLink")

# --- Dual MongoDB Config ---
DATABASE_URI = os.environ.get("DATABASE_URI", "")          # DB 1 (Primary Cluster)
DATABASE_URI_2 = os.environ.get("DATABASE_URI_2", "")      # DB 2 (Secondary Cluster)
USE_SECOND_DB = os.environ.get("USE_SECOND_DB", "False").strip().lower() in ("true", "1", "yes")

# --- Web Server Port ---
PORT = int(os.environ.get("PORT", "8080"))
