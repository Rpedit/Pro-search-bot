import re
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
        file_name = getattr(media, "file_name", "Unknown File")
        file_size = getattr(media, "file_size", 0)
        file_type = media.file_type.name if hasattr(media, "file_type") else "DOCUMENT"

        query = """
        INSERT OR IGNORE INTO files (file_id, file_name, file_size, file_type, caption)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            await self.client.execute(query, [file_id, file_name, file_size, file_type, caption or ""])
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    async def search_files(self, search_text, limit=10, offset=0):
        # Dots, underscores, hyphens, brackets ko space me convert karta hai
        cleaned = re.sub(r"[\.\_\-\[\]\(\)\+]", " ", search_text)
        words = [w.strip() for w in cleaned.split() if len(w.strip()) > 0]
        
        if not words:
            return []

        # Har search word ke liye LIKE condition (case-insensitive)
        conditions = " AND ".join(["LOWER(file_name) LIKE ?" for _ in words])
        params = [f"%{w.lower()}%" for w in words]
        params.extend([limit, offset])

        query = f"""
        SELECT file_id, file_name, file_size FROM files
        WHERE {conditions}
        LIMIT ? OFFSET ?
        """
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
        except Exception as e:
            print(f"Total Files Count Error: {e}")
        return 0

db = Database()
