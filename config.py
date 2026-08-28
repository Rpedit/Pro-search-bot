import os
import re

# Telegram API Credentials (Render Environment Variables se load honge)
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# --- Dual MongoDB Setup ---
DATABASE_URI_1 = os.environ.get(
    "DATABASE_URI_1", 
    "mongodb+srv://s78890881_db_user:QzK0cTkyeAjb1qHq@cluster0.tjx6mjc.mongodb.net/?appName=Cluster0"
)
DATABASE_URI_2 = os.environ.get("DATABASE_URI_2", "")  # Overflow Database (Optional)
DATABASE_NAME = os.environ.get("DATABASE_NAME", "AutoFilterBot")

# --- Force Subscription ---
raw_force_sub = os.environ.get("FORCE_SUB_CHANNEL", "-1002855667443").strip()
FORCE_SUB_CHANNEL = int(raw_force_sub) if raw_force_sub.startswith("-100") else raw_force_sub
FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/")  # Apne Force Sub channel ka t.me link yahan dalein

# --- Movie Storage Channels ---
raw_channels = os.environ.get("CHANNELS", "-1003968479864")
CHANNELS = [int(x) for x in re.split(r'[,\s]+', raw_channels.strip()) if x]

# --- Bot Admins ---
raw_admins = os.environ.get("ADMINS", "7067885693")
ADMINS = [int(x) for x in re.split(r'[,\s]+', raw_admins.strip()) if x]
