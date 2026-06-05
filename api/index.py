import os
import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
APP_URL = os.environ.get("APP_URL", "")

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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        logger.info(f"GET {path}")

        if path in ("/", "/api"):
            self.send_json(200, {
                "status": "running",
                "bot": "za-bot-teletaks",
                "set_webhook": f"{APP_URL}/api/setwebhook",
                "webhook_info": f"{APP_URL}/api/info",
            })
        elif path in ("/setwebhook", "/api/setwebhook"):
            self.handle_set_webhook()
        elif path in ("/deletewebhook", "/api/deletewebhook"):
            self.handle_delete_webhook()
        elif path in ("/info", "/api/info"):
            self.handle_webhook_info()
        else:
            self.send_json(404, {"detail": "Not Found", "path": path})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        logger.info(f"POST {path}")

        if path in ("/", "/api", "/webhook", "/api/webhook"):
            self.handle_webhook(body)
        else:
            self.send_json(404, {"detail": "Not Found", "path": path})

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def handle_webhook(self, body):
        import asyncio

        try:
            data = json.loads(body)
            logger.info(f"Webhook update_id: {data.get('update_id')}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._process_update(data))
            loop.close()
            self.send_json(200, {"ok": True})
        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            self.send_json(500, {"ok": False, "error": str(e)[:200]})

    async def _process_update(self, data):
        from telegram import Update

        app = await get_telegram_app()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)

    def handle_set_webhook(self):
        import asyncio

        try:
            base = APP_URL
            if not base:
                host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "")
                proto = self.headers.get("X-Forwarded-Proto", "https")
                base = f"{proto}://{host}"

            url = f"{base}/api"
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._set_webhook(url))
            loop.close()
        except Exception as e:
            logger.error(f"Set webhook error: {e}")
            self.send_json(500, {"ok": False, "error": str(e)[:200]})

    async def _set_webhook(self, url):
        app = await get_telegram_app()
        result = await app.bot.set_webhook(url=url)
        self.send_json(200, {"ok": result, "webhook_url": url})

    def handle_delete_webhook(self):
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._delete_webhook())
            loop.close()
        except Exception as e:
            logger.error(f"Delete webhook error: {e}")
            self.send_json(500, {"ok": False, "error": str(e)[:200]})

    async def _delete_webhook(self):
        app = await get_telegram_app()
        result = await app.bot.delete_webhook()
        self.send_json(200, {"ok": result})

    def handle_webhook_info(self):
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._webhook_info())
            loop.close()
        except Exception as e:
            logger.error(f"Webhook info error: {e}")
            self.send_json(500, {"ok": False, "error": str(e)[:200]})

    async def _webhook_info(self):
        app = await get_telegram_app()
        info = await app.bot.get_webhook_info()
        self.send_json(200, {
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
        })

    def log_message(self, format, *args):
        logger.info(f"{self.command} {self.path} - {args[0] if args else ''}")

    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})
