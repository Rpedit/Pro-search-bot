from contextlib import asynccontextmanager
from fastapi import FastAPI
from bot import bot
from database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Database & Bot init
    await db.connect()
    await bot.start()
    print("🚀 Bot & Turso DB Started Successfully!")
    yield
    # Shutdown
    await bot.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "running", "service": "HD Pro Search Bot"}

@app.get("/health")
def health():
    return {"status": "ok"}
