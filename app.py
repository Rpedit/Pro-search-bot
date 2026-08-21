from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running healthy on Render!"}

@app.get("/health")
def health():
    return {"status": "ok"}
