import asyncio
from fastapi import FastAPI
from bot import bot
from database import db

app = FastAPI()

@app.on_event("startup")
async def start_services():
    await db.connect()
    await bot.start()
    print("🚀 Bot and Database Started Successfully via FastAPI!")

@app.on_event("shutdown")
async def stop_services():
    await bot.stop()

@app.get("/")
def home():
    return {"status": "running", "bot": "HD Pro Search"}
