import libsql_client
from config import TURSO_DB_URL, TURSO_AUTH_TOKEN

class Database:
    def __init__(self):
        self.url = TURSO_DB_URL
        self.token = TURSO_AUTH_TOKEN
        self.client = None

    async def connect(self):
        if not self.client:
            self.client = libsql_client.create_client(
                url=self.url,
                auth_token=self.token
            )
            await self.init_db()

    async def init_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE,
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            caption TEXT
        );
        """
        try:
            await self.client.execute(query)
        except Exception as e:
            print(f"Table Init: {e}")

    async def save_file(self, media, caption=""):
        file_id = media.file_id
        file_name = getattr(media, "file_name", None)
        if not file_name:
            file_name = caption.strip().split("\n")[0][:120] if caption else f"File_{file_id[:8]}"

        file_size = getattr(media, "file_size", 0)
        file_type = media.file_type.name if hasattr(media, "file_type") else "DOCUMENT"

        query = """
        INSERT OR IGNORE INTO files (file_id, file_name, file_size, file_type, caption)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            await self.client.execute(query, [file_id, str(file_name), int(file_size), file_type, caption or ""])
            return True
        except Exception as e:
            print(f"Save Error: {e}")
            return False

    async def search_files(self, search_text, limit=10, offset=0):
        cleaned = search_text.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        words = [w.strip() for w in cleaned.split() if w.strip()]
        
        if not words:
            return []

        # Sabhi possible text fields me case-insensitive wildcard search
        conditions = []
        params = []
        for word in words:
            conditions.append("(LOWER(file_name) LIKE ? OR LOWER(caption) LIKE ?)")
            params.extend([f"%{word.lower()}%", f"%{word.lower()}%"])

        sql_where = " AND ".join(conditions)
        query = f"SELECT rowid, file_id, file_name, file_size FROM files WHERE {sql_where} LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

        try:
            res = await self.client.execute(query, params)
            results = []
            for row in res.rows:
                # Row id (SQLite default rowid agar id missing ho)
                r_id = row[0] if isinstance(row, (list, tuple)) else row.get("rowid", row.get("id", 1))
                f_name = row[2] if isinstance(row, (list, tuple)) else row.get("file_name", "Unknown File")
                f_size = row[3] if isinstance(row, (list, tuple)) else row.get("file_size", 0)
                results.append((r_id, f_name, f_size))
            return results
        except Exception as e:
            print(f"Search Query Error: {e}")
            return []

    async def get_file_by_id(self, row_id):
        query = "SELECT file_id, file_name, file_size, caption FROM files WHERE rowid = ? OR id = ? LIMIT 1"
        try:
            res = await self.client.execute(query, [int(row_id), int(row_id)])
            if res.rows:
                row = res.rows[0]
                if isinstance(row, (list, tuple)):
                    return (row[0], row[1], row[2], row[3])
                return (row.get("file_id"), row.get("file_name"), row.get("file_size"), row.get("caption"))
        except Exception as e:
            print(f"Get File Error: {e}")
        return None

    async def total_files(self):
        try:
            res = await self.client.execute("SELECT COUNT(*) FROM files")
            if res.rows:
                row = res.rows[0]
                return row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
        except Exception:
            return 0

db = Database()
