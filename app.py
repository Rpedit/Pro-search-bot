from fastapi import FastAPI

app = FastAPI()

@app.get("/")
@app.head("/")
async def home():
    return {"status": "Bot is running healthy on Render!"}

@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok"}
