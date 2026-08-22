import os
from dotenv import load_dotenv

# .env file se secret variables ko load karta hai
load_dotenv()

# --- TELEGRAM CORE API CREDENTIALS ---
# Telegram API ID (my.telegram.org se prapt hota hai)
API_ID = int(os.getenv("API_ID", "25135658"))

# Telegram API Hash (Account authentication aur security ke liye secret key)
API_HASH = os.getenv("API_HASH", "8bc184fb03aecc4c50f47c7f5aef3177")

# Telegram Bot Token (BotFather dwara provide kiya gaya bot ka access token)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")


# --- CHANNELS & ADMINS CONFIGURATION ---
# Database Channel: Jahan bot media files, movies ya links backup/store karta hai
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1003968479864"))

# Force Subscribe (FSUB): User ko bot use karne se pehle is channel ko join karna zaroori hota hai
FSUB_CHANNEL = os.getenv("FSUB_CHANNEL", "-1002855667443").replace("@", "https://t.me/HDProSearch").strip()

# Admin IDs: Bot ke owners/admins ki list jinko special commands aur control milta hai
ADMINS_RAW = os.getenv("ADMINS", "7067885693")
ADMINS = [int(x) for x in ADMINS_RAW.split() if x.strip().lstrip("-").isdigit()]


# --- TURSO DATABASE SETTINGS (CLOUD DB / AUTO-INDEX STORAGE) ---
# Turso Database URL: Jahan user data, search index aur files metadata sync/save hote hain
TURSO_DB_URL = os.getenv("TURSO_DB_URL", "https://movie-db-rpedit.aws-ap-south-1.turso.io")

# Turso Auth Token: Cloud database ko read/write karne ke liye secure access key (JWT)
TURSO_AUTH_TOKEN = os.getenv(
    "TURSO_AUTH_TOKEN", 
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODc0MDY4NjQsImlkIjoiMDFhMDI5YmEtNDAwMS03M2VhLTg3NzgtZjgxNjY0NjFjNWE5Iiwia2lkIjoicm5TUVdMeFNSUWxERkxfUTgwZzhzYi1haE81emZuM1lMR2cwQzhVSDZ3TSIsInJpZCI6IjBhOGQwOWIwLWI0MTMtNGEwMy1iZDNlLTExZDFjOTc1NGFmNiJ9.dJaBdMA-5CmlwLM-BSEpIEHmTquq1OO4hv1Y24WGO5IL46br2lC1VbCjeQjwR3TjFN0WKWO97E6S8GyC2y_yCw"
)


# --- URL SHORTENER SETTINGS (MONETIZATION & LINK CONVERSION) ---
# Shortener API: Link shortener service ka verification API key
SHORTENER_API = os.getenv("SHORTENER_API", "").strip()

# Shortener URL: Jis website/domain se links short hokar redirect honge
SHORTENER_URL = os.getenv("SHORTENER_URL", "").strip()
