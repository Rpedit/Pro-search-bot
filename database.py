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
        # Clean special chars for matching
        clean_text = search_text.strip().replace(" ", "%")
        query = """
        SELECT file_id, file_name, file_size FROM files
        WHERE file_name LIKE ?
        LIMIT ? OFFSET ?
        """
        res = await self.client.execute(query, [f"%{clean_text}%", limit, offset])
        return res.rows

    async def get_file(self, file_id):
        query = "SELECT file_id, file_name, file_size, caption FROM files WHERE file_id = ?"
        res = await self.client.execute(query, [file_id])
        if res.rows:
            return res.rows[0]
        return None

    async def total_files(self):
        res = await self.client.execute("SELECT COUNT(*) FROM files")
        return res.rows[0][0] if res.rows else 0

db = Database()
