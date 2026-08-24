import logging
import libsql_client
from config import TURSO_DB_URL, TURSO_AUTH_TOKEN

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, url: str, auth_token: str):
        # LibSQL standard HTTP/HTTPS or LibSQL URL handling
        self.url = url
        self.auth_token = auth_token
        self._client = None

    def get_client(self):
        # Single client instance manage karta hai taaki unnecessary handshakes na hon
        if self._client is None:
            self._client = libsql_client.create_client(
                url=self.url,
                auth_token=self.auth_token
            )
        return self._client

    async def setup(self):
        client = self.get_client()
        try:
            await client.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT UNIQUE,
                    file_name TEXT,
                    file_size TEXT
                )
            """)
            # Search fast karne ke liye index
            await client.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_name ON files(file_name)
            """)
            logger.info("Turso Database Table setup completed.")
        except Exception as e:
            logger.error(f"DB Setup Error: {e}")
            raise e

    async def add_file(self, file_id: str, file_name: str, file_size: str):
        client = self.get_client()
        try:
            await client.execute(
                "INSERT OR IGNORE INTO files (file_id, file_name, file_size) VALUES (?, ?, ?)",
                [file_id, file_name, str(file_size)]
            )
            return True
        except Exception as e:
            logger.error(f"Add File Error: {e}")
            return False

    async def search_files(self, query: str, max_results: int = 10):
        client = self.get_client()
        try:
            # Case-insensitive LIKE query using LOWER()
            sql = "SELECT file_id, file_name, file_size FROM files WHERE LOWER(file_name) LIKE ? LIMIT ?"
            result = await client.execute(sql, [f"%{query.lower()}%", max_results])
            
            files = []
            for row in result.rows:
                files.append({
                    "file_id": str(row[0]),
                    "file_name": str(row[1]),
                    "file_size": str(row[2]) if len(row) > 2 else ""
                })
            return files
        except Exception as e:
            logger.error(f"Search Files DB Error: {e}")
            return []

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

db = Database(TURSO_DB_URL, TURSO_AUTH_TOKEN)
