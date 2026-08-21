from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/")
@app.head("/")
async def home():
    return Response(content='{"status": "Bot is running healthy on Render!"}', media_type="application/json")

@app.get("/health")
@app.head("/health")
async def health():
    return Response(content='{"status": "ok"}', media_type="application/json")
