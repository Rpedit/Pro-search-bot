import asyncio
import traceback
import sys
from aiohttp import web
from pyrogram import idle
from bot import bot
from config import PORT

async def handle_ping(request):
    return web.Response(text="Bot is running 24/7 Alive!")

async def start_web_server():
    try:
        app = web.Application()
        app.router.add_get("/", handle_ping)
        app.router.add_get("/health", handle_ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        print(f"[WEB] Ping server successfully bound to port {PORT}", flush=True)
    except Exception as e:
        print(f"[WEB ERROR] Failed to start web server: {e}", flush=True)
        traceback.print_exc()

async def main():
    print("[INIT] Starting application...", flush=True)
    
    # 1. Web Server ko background me turant start karein taaki Render port detect kar sake
    asyncio.create_task(start_web_server())
    
    try:
        # Thoda gap taaki web server bind ho jaye
        await asyncio.sleep(2)
        
        print("[BOT] Connecting to Telegram servers...", flush=True)
        await bot.start()
        
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass

        bot_info = await bot.get_me()
        print(f"\n========================================", flush=True)
        print(f"BOT STARTED SUCCESSFULLY: @{bot_info.username}", flush=True)
        print(f"========================================\n", flush=True)
        
        # Bot ko active rakhne ke liye idle loop
        await idle()
        await bot.stop()
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Bot failed to start:", flush=True)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.", flush=True)
