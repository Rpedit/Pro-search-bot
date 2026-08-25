import motor.motor_asyncio
from config import DATABASE_URI, DATABASE_URI_2, USE_SECOND_DB

# Primary Database (DB 1)
client1 = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI) if DATABASE_URI else None
db1 = client1["AutoFilterBot"] if client1 else None
col1 = db1["files"] if db1 is not None else None

# Secondary Database (DB 2)
client2 = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI_2) if DATABASE_URI_2 else None
db2 = client2["AutoFilterBot"] if client2 else None
col2 = db2["files"] if db2 is not None else None

def get_active_collection():
    """Nayi files save karne ke liye active database return karta hai"""
    if USE_SECOND_DB and col2 is not None:
        return col2
    return col1

async def save_file(media):
    """File details database me index karne ke liye"""
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

async def search_db(query: str, limit: int = 300):
    """Dono databases (DB 1 + DB 2) me search karke combined list return karta hai"""
    regex = {"file_name": {"$regex": query, "$options": "i"}}
    results = []

    if col1 is not None:
        res1 = await col1.find(regex).to_list(length=limit)
        results.extend(res1)

    if col2 is not None:
        res2 = await col2.find(regex).to_list(length=limit)
        results.extend(res2)

    # Unique files filter (by file_id)
    seen = set()
    unique_results = []
    for item in results:
        if item["file_id"] not in seen:
            seen.add(item["file_id"])
            unique_results.append(item)

    return unique_results

async def get_file(file_id: str):
    """File send karne ke liye document fetch karta hai"""
    if col1 is not None:
        file_data = await col1.find_one({"file_id": file_id})
        if file_data:
            return file_data
    if col2 is not None:
        file_data = await col2.find_one({"file_id": file_id})
        if file_data:
            return file_data
    return None
