import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from telegram import Update
from telegram.ext import Application

from bot.config import BOT_TOKEN, APP_URL
from bot.handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="za-bot-teletaks")
telegram_app: Application | None = None


async def get_bot_app() -> Application:
    global telegram_app
    if telegram_app is None:
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN tidak ditemukan. Set di environment variables.")
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        register_handlers(telegram_app)
        await telegram_app.initialize()
        await telegram_app.start()
        logger.info("Bot application initialized")
    return telegram_app


@app.on_event("shutdown")
async def shutdown():
    global telegram_app
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
        logger.info("Bot application stopped")


@app.post("/api/bot")
async def webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received update_id: {body.get('update_id')}")
        tg_app = await get_bot_app()
        update = Update.de_json(body, tg_app.bot)
        await tg_app.process_update(update)
        return JSONResponse(content={"ok": True})
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/bot")
async def index():
    return {
        "status": "running",
        "message": "za-bot-teletaks Telegram Bot is active",
    }


@app.get("/api/bot/setwebhook")
async def set_webhook():
    if not APP_URL:
        return {"ok": False, "error": "APP_URL tidak ditemukan di environment"}
    try:
        tg_app = await get_bot_app()
        url = f"{APP_URL}/api/bot"
        result = await tg_app.bot.set_webhook(url=url)
        return {"ok": result, "webhook_url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/bot/deletewebhook")
async def delete_webhook():
    try:
        tg_app = await get_bot_app()
        result = await tg_app.bot.delete_webhook()
        return {"ok": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
