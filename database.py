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
        
        # Video/Audio me file_name None hota hai, isliye fallback caption ya default name
        file_name = getattr(media, "file_name", None)
        if not file_name:
            if caption:
                # Caption ki pehli line ko file name bana lo
                file_name = caption.split("\n")[0][:100]
            else:
                file_name = f"File_{file_id[:8]}"

        file_size = getattr(media, "file_size", 0)
        file_type = media.file_type.name if hasattr(media, "file_type") else "DOCUMENT"

        query = """
        INSERT OR IGNORE INTO files (file_id, file_name, file_size, file_type, caption)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            await self.client.execute(query, [file_id, str(file_name), file_size, file_type, caption or ""])
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    async def search_files(self, search_text, limit=10, offset=0):
        # Clean text
        raw_words = re.split(r"[\s\.\_\-\[\]\(\)\+]+", search_text.strip())
        words = [w.lower() for w in raw_words if len(w) > 0]
        
        if not words:
            return []

        # File name ya Caption dono me search karega
        conditions = []
        params = []
        for w in words:
            conditions.append("(LOWER(file_name) LIKE ? OR LOWER(caption) LIKE ?)")
            params.extend([f"%{w}%", f"%{w}%"])

        where_clause = " AND ".join(conditions)
        params.extend([limit, offset])

        query = f"""
        SELECT file_id, file_name, file_size FROM files
        WHERE {where_clause}
        LIMIT ? OFFSET ?
        """
        try:
            res = await self.client.execute(query, params)
            results = []
            for row in res.rows:
                # Turso client row handling
                if hasattr(row, "__getitem__"):
                    f_id = row[0]
                    f_name = row[1]
                    f_size = row[2]
                else:
                    f_id = getattr(row, "file_id", "")
                    f_name = getattr(row, "file_name", "")
                    f_size = getattr(row, "file_size", 0)
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
                if hasattr(row, "__getitem__"):
                    return (row[0], row[1], row[2], row[3])
                return (row.file_id, row.file_name, row.file_size, row.caption)
        except Exception as e:
            print(f"Get File Error: {e}")
        return None

    async def total_files(self):
        try:
            res = await self.client.execute("SELECT COUNT(*) FROM files")
            if res.rows:
                row = res.rows[0]
                return row[0] if hasattr(row, "__getitem__") else getattr(row, "COUNT(*)", 0)
        except Exception as e:
            print(f"Total Files Count Error: {e}")
        return 0

    # Temporary Debugging Function: Dekhne ke liye ki DB me save kya hua hai
    async def get_sample_files(self):
        try:
            res = await self.client.execute("SELECT file_name, file_size FROM files LIMIT 5")
            return [(r[0], r[1]) for r in res.rows]
        except Exception:
            return []

db = Database()
