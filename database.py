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
        await self.client.execute(query)

    async def save_file(self, media, caption=""):
        file_id = media.file_id
        
        # File name extract logic (Telegram video me file_name missing hota hai)
        file_name = getattr(media, "file_name", None)
        if not file_name:
            if caption:
                file_name = caption.strip().split("\n")[0][:120]
            else:
                file_name = f"Movie_{file_id[:8]}"

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
            print(f"Error saving file: {e}")
            return False

    async def search_files(self, search_text, limit=10, offset=0):
        # Text clean karke har word ko extract karein
        cleaned = search_text.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        words = [w.strip() for w in cleaned.split() if w.strip()]
        
        if not words:
            return []

        # Simple & Solid SQLite Substring Search
        conditions = []
        params = []
        for word in words:
            conditions.append("(file_name LIKE ? OR caption LIKE ?)")
            params.extend([f"%{word}%", f"%{word}%"])

        sql_where = " AND ".join(conditions)
        query = f"SELECT file_id, file_name, file_size FROM files WHERE {sql_where} LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])

        try:
            res = await self.client.execute(query, params)
            results = []
            for row in res.rows:
                f_id = row[0] if isinstance(row, (list, tuple)) else row["file_id"]
                f_name = row[1] if isinstance(row, (list, tuple)) else row["file_name"]
                f_size = row[2] if isinstance(row, (list, tuple)) else row["file_size"]
                results.append((f_id, f_name, f_size))
            return results
        except Exception as e:
            print(f"Search Query Error: {e}")
            return []

    async def get_file(self, file_id):
        query = "SELECT file_id, file_name, file_size, caption FROM files WHERE file_id = ?"
        try:
            res = await self.client.execute(query, [file_id])
            if res.rows:
                row = res.rows[0]
                f_id = row[0] if isinstance(row, (list, tuple)) else row["file_id"]
                f_name = row[1] if isinstance(row, (list, tuple)) else row["file_name"]
                f_size = row[2] if isinstance(row, (list, tuple)) else row["file_size"]
                caption = row[3] if isinstance(row, (list, tuple)) else row["caption"]
                return (f_id, f_name, f_size, caption)
        except Exception as e:
            print(f"Get File Error: {e}")
        return None

    async def total_files(self):
        try:
            res = await self.client.execute("SELECT COUNT(*) FROM files")
            if res.rows:
                return res.rows[0][0] if isinstance(res.rows[0], (list, tuple)) else res.rows[0]["COUNT(*)"]
        except Exception:
            return 0

db = Database()
