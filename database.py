import libsql_client
from config import TURSO_DB_URL, TURSO_AUTH_TOKEN

# Correct async client method
client = libsql_client.create_client(
    url=TURSO_DB_URL,
    auth_token=TURSO_AUTH_TOKEN
)

# --- INITIALIZE TABLES & INDEXES ---
async def init_db():
    await client.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE,
            file_name TEXT,
            file_size INTEGER,
            caption TEXT
        );
    """)
    await client.execute("CREATE INDEX IF NOT EXISTS idx_file_name ON files(file_name);")
    
    await client.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_banned INTEGER DEFAULT 0
        );
    """)
    print("[DB]: Turso 9GB Database Connected & Tables Initialized!", flush=True)

# --- STATS FUNCTION ---
async def get_db_stats():
    res_files = await client.execute("SELECT COUNT(*) FROM files;")
    total_files = res_files.rows[0][0] if res_files.rows else 0
    
    res_users = await client.execute("SELECT COUNT(*) FROM users;")
    total_users = res_users.rows[0][0] if res_users.rows else 0
    
    res_banned = await client.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1;")
    banned_users = res_banned.rows[0][0] if res_banned.rows else 0
    
    return {
        "total_files": total_files,
        "total_users": total_users,
        "banned_users": banned_users,
        "storage_type": "Turso libSQL (9 GB Free Pool)"
    }

# --- USER MANAGEMENT (BAN / UNBAN) ---
async def add_user(user_id: int):
    await client.execute(
        "INSERT INTO users (user_id, is_banned) VALUES (?, 0) ON CONFLICT(user_id) DO NOTHING;",
        [user_id]
    )

async def ban_user(user_id: int):
    await client.execute(
        "INSERT INTO users (user_id, is_banned) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET is_banned = 1;",
        [user_id]
    )

async def unban_user(user_id: int):
    await client.execute(
        "UPDATE users SET is_banned = 0 WHERE user_id = ?;",
        [user_id]
    )

async def is_user_banned(user_id: int) -> bool:
    res = await client.execute("SELECT is_banned FROM users WHERE user_id = ?;", [user_id])
    if res.rows:
        return bool(res.rows[0][0])
    return False

# --- FILE OPERATIONS ---
async def save_file(file_id: str, file_name: str, file_size: int, caption: str = "") -> bool:
    try:
        res = await client.execute(
            "INSERT OR IGNORE INTO files (file_id, file_name, file_size, caption) VALUES (?, ?, ?, ?);",
            [file_id, file_name.lower(), file_size, caption]
        )
        return res.rows_affected > 0
    except Exception:
        return False

async def get_file_by_id(db_id: str):
    try:
        res = await client.execute("SELECT id, file_id, file_name, file_size, caption FROM files WHERE id = ?;", [int(db_id)])
        if res.rows:
            r = res.rows[0]
            return {
                "_id": r[0],
                "file_id": r[1],
                "file_name": r[2],
                "file_size": r[3],
                "caption": r[4]
            }
    except Exception:
        pass
    return None

async def search_files(query: str, offset: int = 0, limit: int = 10):
    words = query.strip().split()
    like_pattern = "%" + "%".join(words) + "%"
    
    res = await client.execute(
        "SELECT id, file_id, file_name, file_size, caption FROM files WHERE file_name LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?;",
        [like_pattern.lower(), limit, offset]
    )
    
    results = []
    for r in res.rows:
        results.append({
            "_id": r[0],
            "file_id": r[1],
            "file_name": r[2],
            "file_size": r[3],
            "caption": r[4]
        })
    return results

async def count_files(query: str) -> int:
    words = query.strip().split()
    like_pattern = "%" + "%".join(words) + "%"
    res = await client.execute(
        "SELECT COUNT(*) FROM files WHERE file_name LIKE ?;",
        [like_pattern.lower()]
    )
    return res.rows[0][0] if res.rows else 0

# --- DELETE OPERATIONS ---
async def delete_single_file(file_id: str = None, file_name: str = None) -> int:
    if file_id:
        res = await client.execute("DELETE FROM files WHERE file_id = ?;", [file_id])
        return res.rows_affected
    elif file_name:
        words = file_name.strip().split()
        like_pattern = "%" + "%".join(words) + "%"
        res = await client.execute("DELETE FROM files WHERE id IN (SELECT id FROM files WHERE file_name LIKE ? LIMIT 1);", [like_pattern.lower()])
        return res.rows_affected
    return 0

async def delete_files_by_name(query: str) -> int:
    words = query.strip().split()
    like_pattern = "%" + "%".join(words) + "%"
    res = await client.execute("DELETE FROM files WHERE file_name LIKE ?;", [like_pattern.lower()])
    return res.rows_affected
