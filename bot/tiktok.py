import re
import asyncio
import httpx


TIKTOK_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|m\.)?(tiktok\.com|tiktok\.com/@[\w.-]+/video/\d+)",
)
TIKTOK_SHORT_PATTERN = re.compile(r"https?://(?:vm\.|vt\.)?tiktok\.com/\S+")


def is_tiktok_url(text: str) -> bool:
    return bool(TIKTOK_PATTERN.search(text) or TIKTOK_SHORT_PATTERN.search(text))


async def get_tiktok_video_url(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://tikwm.com/api/",
                data={"url": url, "hd": 1},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            data = resp.json()
            if data.get("code") != 0:
                return None
            return data["data"].get("play") or data["data"].get("wmplay")
    except Exception:
        return await _ytdlp_get_url(url)


async def _ytdlp_get_url(url: str) -> str | None:
    import yt_dlp

    loop = asyncio.get_event_loop()

    def extract():
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best[ext=mp4]/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url")

    try:
        return await loop.run_in_executor(None, extract)
    except Exception:
        return None
