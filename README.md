# 🎬 AutoFilter Movie Telegram Bot

A fast, lightweight, and modern Telegram Movie & Web Series Search Bot built using **Pyrogram** and powered by **Turso (libSQL/SQLite Cloud)** database.

---

## ✨ Features

- 🔍 **Instant Search Engine:** Fast multi-word indexing and case-insensitive matching.
- 🔄 **Landscape Mode Full Name:** Automatically formatted file titles that reveal complete details upon rotating the device.
- 🚫 **Duplicate Prevention:** Smart filters automatically skip files with matching `file_id` or same name and size.
- 🗑 **Auto-Delete Engine:**
  - Auto-deletes delivered files after 1 minute (60 seconds) with clear warnings.
  - Auto-deletes search results after 4.5 minutes with custom copyright warning alerts.
- 📑 **Dynamic Pagination:** Interactive `⏪ Previous`, page counter, and `Next ⏩` controls.
- 📢 **Force Subscription (FSub):** Ensures users join your update channel before accessing files.
- ⚡ **Admin Control Suite:** Broadcast tool, ban/unban controls, single/batch file removal, and 1-click full database wipe (`/clearall`).

---

## 🛠️ Environment Variables (`config.py`)

Set up the following variables in your `config.py` or host environment:

| Variable | Description |
| :--- | :--- |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TURSO_DB_URL` | Turso libSQL Cloud Database URL (`libsql://...`) |
| `TURSO_AUTH_TOKEN` | Turso Database JWT Authentication Token |
| `DB_CHANNEL` | Telegram Channel ID used for auto-indexing media files |
| `FSUB_CHANNEL` | Channel Username or ID for mandatory subscription check |
| `ADMINS` | List of Admin Telegram User IDs (e.g., `[123456789]`) |

---

## 🤖 Bot Commands

### User Commands
- `/start` - Start the bot, check subscription status, or retrieve requested files.
- `Send Movie Name` - Search for matching movies or series in the database.

### Admin Commands
- `/stats` - View total files, total users, and banned users.
- `/broadcast` - Broadcast text or media messages to all active users with confirmation.
- `/ban <user_id>` - Ban a user from using the bot.
- `/unban <user_id>` - Unban a user.
- `/delete` - Reply to a media file or specify a name to remove it from the DB.
- `/deletefiles <Movie Name>` - Delete all files associated with a specific title.
- `/clearall` - ⚠️ Completely wipe all indexed media files from the database (with safety confirmation).

---

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/your-repo-name.git](https://github.com/yourusername/your-repo-name.git)
   cd your-repo-name
