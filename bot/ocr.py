import asyncio
import base64
from io import BytesIO

import httpx

from bot.config import OCR_API_KEY, OCR_ENGINE


async def ocr_image(image_bytes: bytes) -> str | None:
    if OCR_ENGINE == "googlevision" and OCR_API_KEY:
        return await _google_vision_ocr(image_bytes)

    return await _ocrspace_ocr(image_bytes)


async def _google_vision_ocr(image_bytes: bytes) -> str | None:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "requests": [
            {
                "image": {"content": encoded},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }
    url = f"https://vision.googleapis.com/v1/images:annotate?key={OCR_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            texts = data.get("responses", [{}])[0].get("textAnnotations", [])
            if texts:
                return texts[0].get("description", "")
    except Exception:
        pass
    return None


async def _ocrspace_ocr(image_bytes: bytes) -> str | None:
    api_key = OCR_API_KEY or "helloworld"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.ocr.space/parse/image",
                files={"file": ("image.png", image_bytes)},
                data={
                    "apikey": api_key,
                    "language": "eng",
                    "isOverlayRequired": False,
                },
            )
            data = resp.json()
            if data.get("IsErroredOnProcessing"):
                return None
            results = data.get("ParsedResults", [])
            if results:
                return results[0].get("ParsedText", "")
    except Exception:
        pass
    return None
