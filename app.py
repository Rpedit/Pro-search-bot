from contextlib import asynccontextmanager
from fastapi import FastAPI
from bot import app as bot_client  # bot.py se app client ko import karo
from database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Database & Bot init
    await db.setup()
    await bot_client.start()
    print("🚀 Bot & Turso DB Started Successfully!")
    yield
    # Shutdown
    await bot_client.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "running", "service": "HD Pro Search Bot"}

@app.get("/health")
def health():
    return {"status": "ok"}
