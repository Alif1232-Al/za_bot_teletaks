import os
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from telegram import Update
from telegram.ext import Application

from bot.config import BOT_TOKEN
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


def get_base_url(request: Request = None) -> str:
    url = os.environ.get("APP_URL", "")
    if not url and request:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        proto = request.headers.get("x-forwarded-proto", "https")
        url = f"{proto}://{host}"
    return url.rstrip("/")


@app.get("/api")
async def root(request: Request):
    base = get_base_url(request)
    return {
        "status": "running",
        "bot": "za-bot-teletaks",
        "webhook_url": f"{base}/api",
        "set_webhook": f"{base}/api/setwebhook",
        "webhook_info": f"{base}/api/info",
    }


@app.post("/api")
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


@app.post("/api/webhook")
async def webhook_alt(request: Request):
    return await webhook(request)


@app.get("/api/setwebhook")
async def set_webhook(request: Request):
    try:
        base = get_base_url(request)
        tg_app = await get_bot_app()
        url = f"{base}/api"
        result = await tg_app.bot.set_webhook(url=url)
        return {"ok": result, "webhook_url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/deletewebhook")
async def delete_webhook():
    try:
        tg_app = await get_bot_app()
        result = await tg_app.bot.delete_webhook()
        return {"ok": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/info")
async def webhook_info():
    try:
        tg_app = await get_bot_app()
        info = await tg_app.bot.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "ip_address": info.ip_address,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
