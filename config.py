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

# --- TURSO DATABASE SETTINGS (9 GB FREE) ---
TURSO_DB_URL = os.getenv("TURSO_DB_URL", "libsql://movie-db-rpedit.aws-ap-south-1.turso.io")
TURSO_AUTH_TOKEN = os.getenv(
    "TURSO_AUTH_TOKEN", 
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODc0MDY4NjQsImlkIjoiMDFhMDI5YmEtNDAwMS03M2VhLTg3NzgtZjgxNjY0NjFjNWE5Iiwia2lkIjoicm5TUVdMeFNSUWxERkxfUTgwZzhzYi1haE81emZuM1lMR2cwQzhVSDZ3TSIsInJpZCI6IjBhOGQwOWIwLWI0MTMtNGEwMy1iZDNlLTExZDFjOTc1NGFmNiJ9.dJaBdMA-5CmlwLM-BSEpIEHmTquq1OO4hv1Y24WGO5IL46br2lC1VbCjeQjwR3TjFN0WKWO97E6S8GyC2y_yCw"
)

# Shortener Settings (Optional)
SHORTENER_API = os.getenv("SHORTENER_API", "").strip()
SHORTENER_URL = os.getenv("SHORTENER_URL", "").strip()
