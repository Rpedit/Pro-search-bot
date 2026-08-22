import re
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI_1, DATABASE_URI_2, USE_SECOND_DB

# --- DB 1 (PRIMARY) ---
client1 = AsyncIOMotorClient(DATABASE_URI_1)
db1 = client1["TelegramAutoFilterBot"]
files_col1 = db1["files"]
users_col = db1["users"]  # Users & Ban list Primary DB me rahegi

# --- DB 2 (SECONDARY / BACKUP) ---
client2 = AsyncIOMotorClient(DATABASE_URI_2) if DATABASE_URI_2 else None
db2 = client2["TelegramAutoFilterBot2"] if client2 else None
files_col2 = db2["files"] if db2 else None

async def init_db():
    await files_col1.create_index([("file_name", "text")])
    if files_col2 is not None:
        await files_col2.create_index([("file_name", "text")])
    print("[DB]: Indexes initialized successfully!", flush=True)

# Select active collection for saving new files
def get_active_files_col():
    if USE_SECOND_DB and files_col2 is not None:
        return files_col2
    return files_col1

# --- BOT & DATABASE STATS ---
async def get_db_stats():
    total_users = await users_col.count_documents({})
    banned_users = await users_col.count_documents({"is_banned": True})
    
    db1_files = await files_col1.count_documents({})
    db2_files = await files_col2.count_documents({}) if files_col2 is not None else 0
    total_files = db1_files + db2_files

    return {
        "total_users": total_users,
        "banned_users": banned_users,
        "total_files": total_files,
        "db1_files": db1_files,
        "db2_files": db2_files,
        "active_db": "Database 2" if (USE_SECOND_DB and files_col2 is not None) else "Database 1"
    }

# --- USER MANAGEMENT (BAN / UNBAN) ---
async def add_user(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

async def ban_user(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": True}}, upsert=True)

async def unban_user(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": False}}, upsert=True)

async def is_user_banned(user_id: int) -> bool:
    user = await users_col.find_one({"user_id": user_id})
    return bool(user and user.get("is_banned", False))

# --- FILE OPERATIONS ---
async def save_file(file_id: str, file_name: str, file_size: int, caption: str = ""):
    col = get_active_files_col()
    data = {
        "file_id": file_id,
        "file_name": file_name.lower(),
        "file_size": file_size,
        "caption": caption
    }
    # Check if file already exists in active DB (Duplicate check)
    existing = await col.find_one({"file_id": file_id})
    if not existing:
        await col.update_one({"file_id": file_id}, {"$set": data}, upsert=True)
        return True
    return False

async def get_file_by_id(db_id: str):
    # Pehle DB1 me search karega
    try:
        f = await files_col1.find_one({"_id": ObjectId(db_id)})
        if f: return f
    except Exception:
        pass
    
    # DB1 me na mile toh DB2 me search karega
    if files_col2 is not None:
        try:
            f = await files_col2.find_one({"_id": ObjectId(db_id)})
            if f: return f
        except Exception:
            pass
    return None

async def search_files(query: str, offset: int = 0, limit: int = 10):
    words = query.strip().split()
    pattern = ".*".join([re.escape(w) for w in words])
    regex = re.compile(pattern, re.IGNORECASE)
    
    # DB 1 se search
    results = await files_col1.find({"file_name": regex}).skip(offset).limit(limit).to_list(length=limit)
    
    # Agar DB 1 me kam ya limit se kam mile aur DB 2 active ho toh DB 2 se search
    if files_col2 is not None and len(results) < limit:
        extra_limit = limit - len(results)
        results2 = await files_col2.find({"file_name": regex}).skip(offset).limit(extra_limit).to_list(length=extra_limit)
        results.extend(results2)
        
    return results

async def count_files(query: str) -> int:
    words = query.strip().split()
    pattern = ".*".join([re.escape(w) for w in words])
    regex = re.compile(pattern, re.IGNORECASE)
    
    count1 = await files_col1.count_documents({"file_name": regex})
    count2 = await files_col2.count_documents({"file_name": regex}) if files_col2 is not None else 0
    return count1 + count2

# --- DELETE OPERATIONS ---
async def delete_single_file(file_id: str = None, file_name: str = None):
    query = {}
    if file_id:
        query["file_id"] = file_id
    elif file_name:
        words = file_name.strip().split()
        pattern = ".*".join([re.escape(w) for w in words])
        query["file_name"] = re.compile(pattern, re.IGNORECASE)
    else:
        return 0

    del1 = await files_col1.delete_one(query)
    del2 = await files_col2.delete_one(query) if files_col2 is not None else None
    return del1.deleted_count or (del2.deleted_count if del2 else 0)

async def delete_files_by_name(query: str):
    words = query.strip().split()
    pattern = ".*".join([re.escape(w) for w in words])
    regex = re.compile(pattern, re.IGNORECASE)
    
    del1 = await files_col1.delete_many({"file_name": regex})
    del2 = await files_col2.delete_many({"file_name": regex}) if files_col2 is not None else None
    return del1.deleted_count + (del2.deleted_count if del2 else 0)
