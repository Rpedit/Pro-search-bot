import re
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

client = AsyncIOMotorClient(MONGO_URI)
db = client["TelegramAutoFilterBot"]
files_col = db["files"]
users_col = db["users"]

async def init_db():
    await files_col.create_index([("file_name", "text")])

async def save_file(file_id, file_name, file_size, caption=""):
    data = {
        "file_id": file_id,
        "file_name": file_name.lower(),
        "file_size": file_size,
        "caption": caption
    }
    await files_col.update_one({"file_id": file_id}, {"$set": data}, upsert=True)

async def search_files(query, limit=10):
    # Words ko split karke flexible regex banayega taaki dots aur space dono match ho
    words = query.strip().split()
    pattern = ".*".join([re.escape(w) for w in words])
    regex = re.compile(pattern, re.IGNORECASE)
    return await files_col.find({"file_name": regex}).to_list(length=limit)

async def get_file_by_id(db_id):
    try:
        return await files_col.find_one({"_id": ObjectId(db_id)})
    except Exception:
        return None

async def add_user(user_id):
    await users_col.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
