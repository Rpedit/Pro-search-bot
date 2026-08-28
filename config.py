import os

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# --- Dual MongoDB URLs ---
DATABASE_URI_1 = os.environ.get("DATABASE_URI_1", "mongodb+srv://s78890881_db_user:QzK0cTkyeAjb1qHq@cluster0.tjx6mjc.mongodb.net/?appName=Cluster0")  # Main Database
DATABASE_URI_2 = os.environ.get("DATABASE_URI_2", "")  # Overflow Database (Jab DB 1 full ho)
DATABASE_NAME = os.environ.get("DATABASE_NAME", "AutoFilterBot")

# --- Force Subscription Channel ---
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "-1002855667443") 

CHANNELS = [int(x) if x.startswith("-") else int(x) for x in os.environ.get("CHANNELS", "-1003968479864").split()]
ADMINS = [int(x) for x in os.environ.get("ADMINS", "7067885693").split()]
