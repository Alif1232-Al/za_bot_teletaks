import asyncio
import tempfile
import os
from io import BytesIO

import httpx
from PIL import Image

from bot.config import REMOVE_BG_API_KEY


async def remove_background(image_bytes: bytes) -> bytes | None:
    if REMOVE_BG_API_KEY:
        return await _remove_bg_api(image_bytes)
    return await _remove_bg_local(image_bytes)


async def _remove_bg_api(image_bytes: bytes) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.remove.bg/v1.0/removebg",
                files={"image_file": ("image.png", image_bytes)},
                data={"size": "auto"},
                headers={"X-Api-Key": REMOVE_BG_API_KEY},
            )
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None


async def _remove_bg_local(image_bytes: bytes) -> bytes | None:
    try:
        from rembg import remove

        loop = asyncio.get_event_loop()

        def _remove():
            input_img = Image.open(BytesIO(image_bytes))
            output = remove(input_img)
            buf = BytesIO()
            output.save(buf, format="PNG")
            return buf.getvalue()

        return await loop.run_in_executor(None, _remove)
    except ImportError:
        return None
    except Exception:
        return None
