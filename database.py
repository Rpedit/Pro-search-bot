import re
import motor.motor_asyncio
from config import DATABASE_URI, DATABASE_URI_2, USE_SECOND_DB

# Primary Database Client & Collection
client1 = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI) if DATABASE_URI else None
db1 = client1["AutoFilterBot"] if client1 else None
col1 = db1["files"] if db1 is not None else None

# Secondary Database Client & Collection (Safe Initialization)
client2 = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI_2) if DATABASE_URI_2 else None
db2 = client2["AutoFilterBot"] if client2 else None
col2 = db2["files"] if db2 is not None else None

def get_active_collection():
    if USE_SECOND_DB and col2 is not None:
        return col2
    return col1

async def save_file(media):
    try:
        col = get_active_collection()
        if col is None:
            return False

        file_id = media.file_id
        file_name = getattr(media, "file_name", "Unknown File")
        file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "None")

        exists = await col.find_one({"file_id": file_id})
        if not exists:
            doc = {
                "file_id": file_id,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type
            }
            await col.insert_one(doc)
            return True
        return False
    except Exception as e:
        print(f"[DB ERROR] save_file failed: {e}", flush=True)
        return False

async def search_db(query: str, limit: int = 300):
    try:
        safe_query = re.escape(query)
        regex = {"file_name": {"$regex": safe_query, "$options": "i"}}
        results = []

        if col1 is not None:
            res1 = await col1.find(regex).to_list(length=limit)
            results.extend(res1)

        if col2 is not None:
            res2 = await col2.find(regex).to_list(length=limit)
            results.extend(res2)

        seen = set()
        unique_results = []
        for item in results:
            if item["file_id"] not in seen:
                seen.add(item["file_id"])
                unique_results.append(item)

        return unique_results
    except Exception as e:
        print(f"[DB ERROR] search_db failed: {e}", flush=True)
        return []

async def get_file(file_id: str):
    try:
        if col1 is not None:
            file_data = await col1.find_one({"file_id": file_id})
            if file_data:
                return file_data
        if col2 is not None:
            file_data = await col2.find_one({"file_id": file_id})
            if file_data:
                return file_data
        return None
    except Exception as e:
        print(f"[DB ERROR] get_file failed: {e}", flush=True)
        return None
