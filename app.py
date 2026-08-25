import asyncio
from aiohttp import web
from pyrogram import idle
from bot import bot
from config import PORT

async def handle_ping(request):
    return web.Response(text="Bot is running 24/7 Alive!")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    await start_web()
    await bot.start()
    
    # Purana webhook delete karein taaki long-polling messages turant milein
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    bot_info = await bot.get_me()
    print(f"\n========================================\n", flush=True)
    print(f"BOT ACTIVE: @{bot_info.username}", flush=True)
    print(f"========================================\n", flush=True)
    
    await idle()
    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
