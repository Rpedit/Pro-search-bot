import motor.motor_asyncio
from config import DATABASE_URI_1, DATABASE_URI_2, DATABASE_NAME

client1 = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI_1)
db1 = client1[DATABASE_NAME]
user_col = db1["users"]
media_col_1 = db1["telegram_files"]

client2 = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI_2) if DATABASE_URI_2 else client1
db2 = client2[DATABASE_NAME] if DATABASE_URI_2 else db1
media_col_2 = db2["telegram_files"]

# MongoDB Atlas Free Tier Limit (~512MB), switching safely at 480MB
MAX_DB_SIZE = 480 * 1024 * 1024 

class Database:
    async def add_user(self, user_id):
        if not await user_col.find_one({"_id": user_id}):
            await user_col.insert_one({"_id": user_id})

    async def total_users_count(self):
        return await user_col.count_documents({})

    async def get_active_collection(self):
        try:
            stats = await db1.command("dbStats")
            current_size = stats.get("dataSize", 0) + stats.get("indexSize", 0)
            if current_size >= MAX_DB_SIZE and DATABASE_URI_2:
                return media_col_2
        except Exception:
            pass
        return media_col_1

    async def save_file(self, file_data):
        file_id = file_data.get("file_id")
        exists_1 = await media_col_1.find_one({"file_id": file_id})
        exists_2 = await media_col_2.find_one({"file_id": file_id}) if DATABASE_URI_2 else None

        if exists_1 or exists_2:
            return False

        col = await self.get_active_collection()
        await col.insert_one(file_data)
        return True

    async def search_media(self, query):
        regex = {"file_name": {"$regex": query, "$options": "i"}}
        
        cursor1 = media_col_1.find(regex)
        results1 = await cursor1.to_list(length=30)

        results2 = []
        if DATABASE_URI_2:
            cursor2 = media_col_2.find(regex)
            results2 = await cursor2.to_list(length=30)

        combined = {item["file_id"]: item for item in results1 + results2}
        return list(combined.values())[:50]

db_instance = Database()
