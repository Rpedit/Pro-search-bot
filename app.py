import asyncio
from aiohttp import web
from bot import bot
from config import PORT

async def handle_ping(request):
    return web.Response(text="Bot is running 24/7 Alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await start_web_server()
    await bot.start()
    print(">>> Auto Filter Bot Started Successfully <<<")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
