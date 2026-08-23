import libsql_client
import config

class Database:
    def __init__(self):
        self.url = config.TURSO_DB_URL
        self.token = config.TURSO_AUTH_TOKEN
        self.client = None

    async def connect(self):
        if not self.client:
            self.client = libsql_client.create_client(
                url=self.url,
                auth_token=self.token
            )
            await self.setup_tables()

    async def setup_tables(self):
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
            print(f"[DB INIT ERROR] -> {e}")

    async def save_file(self, media, caption=""):
        file_id = getattr(media, "file_id", None)
        if not file_id:
            return False

        file_name = getattr(media, "file_name", None)
        if not file_name:
            if caption:
                file_name = caption.strip().split("\n")[0][:100]
            else:
                file_name = f"File_{file_id[:8]}"

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
            print(f"[DB SAVE ERROR] -> {e}")
            return False

    async def search_files(self, query_text, limit=10, offset=0):
        # Clean query tokens
        clean_text = "".join([c if c.isalnum() else " " for c in query_text])
        tokens = [w.strip().lower() for w in clean_text.split() if w.strip()]

        if not tokens:
            return []

        # Build SQL condition matching file_name and caption
        conditions = []
        params = []
        for token in tokens:
            conditions.append("(LOWER(file_name) LIKE ? OR LOWER(caption) LIKE ?)")
            params.extend([f"%{token}%", f"%{token}%"])

        where_clause = " AND ".join(conditions)
        query = f"SELECT id, file_id, file_name, file_size FROM files WHERE {where_clause} LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

        try:
            res = await self.client.execute(query, params)
            output = []
            for row in res.rows:
                if isinstance(row, (list, tuple)):
                    row_id = row[0]
                    f_name = row[2] or "Unknown File"
                    f_size = row[3] or 0
                else:
                    row_id = row.get("id") or 1
                    f_name = row.get("file_name") or row.get("caption") or "Unknown File"
                    f_size = row.get("file_size") or 0
                output.append((row_id, f_name, f_size))
            return output
        except Exception as e:
            print(f"[DB SEARCH ERROR] -> {e}")
            return []

    async def get_file_by_id(self, db_id):
        query = "SELECT file_id, file_name, file_size, caption FROM files WHERE id = ? LIMIT 1"
        try:
            res = await self.client.execute(query, [int(db_id)])
            if res.rows:
                row = res.rows[0]
                if isinstance(row, (list, tuple)):
                    return {
                        "file_id": row[0],
                        "file_name": row[1],
                        "file_size": row[2],
                        "caption": row[3]
                    }
                return {
                    "file_id": row.get("file_id"),
                    "file_name": row.get("file_name"),
                    "file_size": row.get("file_size"),
                    "caption": row.get("caption")
                }
        except Exception as e:
            print(f"[DB GET ERROR] -> {e}")
        return None

    async def count_all_files(self):
        try:
            res = await self.client.execute("SELECT COUNT(*) FROM files")
            if res.rows:
                row = res.rows[0]
                return row[0] if isinstance(row, (list, tuple)) else list(row.values())[0]
        except Exception:
            pass
        return 0

db = Database()
