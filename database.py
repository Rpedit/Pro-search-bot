import libsql_client
from config import TURSO_DB_URL, TURSO_AUTH_TOKEN

class Database:
    def __init__(self, url, auth_token):
        self.url = url
        self.auth_token = auth_token

    def get_client(self):
        # libsql-client uses standard create_client
        return libsql_client.create_client(
            url=self.url,
            auth_token=self.auth_token
        )

    async def setup(self):
        # Turso client calls are synchronous or handled via standard execution
        client = self.get_client()
        try:
            client.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT,
                    file_name TEXT,
                    file_size TEXT
                )
            """)
        finally:
            client.close()

    async def add_file(self, file_id, file_name, file_size):
        client = self.get_client()
        try:
            client.execute(
                "INSERT INTO files (file_id, file_name, file_size) VALUES (?, ?, ?)",
                [file_id, file_name, file_size]
            )
        finally:
            client.close()

    async def search_files(self, query, max_results=10):
        client = self.get_client()
        try:
            result = client.execute(
                "SELECT file_id, file_name, file_size FROM files WHERE file_name LIKE ? LIMIT ?",
                [f"%{query}%", max_results]
            )
            files = []
            for row in result.rows:
                files.append({
                    "file_id": row[0],
                    "file_name": row[1],
                    "file_size": row[2]
                })
            return files
        finally:
            client.close()

db = Database(TURSO_DB_URL, TURSO_AUTH_TOKEN)
