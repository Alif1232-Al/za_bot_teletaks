import json
import os
import sys
import logging
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
_telegram_app = None


async def get_telegram_app():
    global _telegram_app
    if _telegram_app is None:
        from telegram.ext import Application
        from bot.handlers import register_handlers

        _telegram_app = Application.builder().token(BOT_TOKEN).build()
        register_handlers(_telegram_app)
        await _telegram_app.initialize()
        await _telegram_app.start()
        logger.info("Telegram app initialized")
    return _telegram_app


async def process_webhook(data):
    from telegram import Update

    app = await get_telegram_app()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)


async def set_webhook_async(base_url):
    from telegram import Bot

    bot = Bot(token=BOT_TOKEN)
    url = f"{base_url}/api"
    result = await bot.set_webhook(url=url)
    await bot.close()
    return result, url


async def delete_webhook_async():
    from telegram import Bot

    bot = Bot(token=BOT_TOKEN)
    result = await bot.delete_webhook()
    await bot.close()
    return result


async def webhook_info_async():
    from telegram import Bot

    bot = Bot(token=BOT_TOKEN)
    info = await bot.get_webhook_info()
    await bot.close()
    return info


def get_base_url(environ):
    url = os.environ.get("APP_URL", "")
    if url:
        return url.rstrip("/")
    host = environ.get("HTTP_X_FORWARDED_HOST") or environ.get("HTTP_HOST", "")
    proto = environ.get("HTTP_X_FORWARDED_PROTO", "https")
    return f"{proto}://{host}"


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/").rstrip("/") or "/"
    method = environ.get("REQUEST_METHOD", "GET")

    logger.info(f"{method} {path}")

    data = None
    status = "200 OK"

    try:
        if method == "GET":
            if path in ("/", "/api"):
                base = get_base_url(environ)
                data = {
                    "status": "running",
                    "bot": "za-bot-teletaks",
                    "webhook_url": f"{base}/api",
                    "set_webhook": f"{base}/api/setwebhook",
                    "info": f"{base}/api/info",
                }
            elif path in ("/setwebhook", "/api/setwebhook"):
                base = get_base_url(environ)
                result, url = asyncio.run(set_webhook_async(base))
                data = {"ok": result, "webhook_url": url}
            elif path in ("/deletewebhook", "/api/deletewebhook"):
                result = asyncio.run(delete_webhook_async())
                data = {"ok": result}
            elif path in ("/info", "/api/info"):
                info = asyncio.run(webhook_info_async())
                data = {
                    "url": info.url,
                    "pending_update_count": info.pending_update_count,
                    "last_error_message": info.last_error_message,
                }
            else:
                status = "404 Not Found"
                data = {"detail": "Not Found", "path": path}

        elif method == "POST":
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            body = environ["wsgi.input"].read(content_length) if content_length else b"{}"

            if path in ("/", "/api", "/webhook", "/api/webhook"):
                payload = json.loads(body)
                logger.info(f"Webhook update_id: {payload.get('update_id')}")
                asyncio.run(process_webhook(payload))
                data = {"ok": True}
            else:
                status = "404 Not Found"
                data = {"detail": "Not Found", "path": path}

        else:
            status = "405 Method Not Allowed"
            data = {"error": "Method not allowed"}

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        status = "500 Internal Server Error"
        data = {"error": str(e)[:200]}

    body = json.dumps(data).encode("utf-8")
    headers = [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
        ("Access-Control-Allow-Origin", "*"),
    ]
    start_response(status, headers)
    return [body]
