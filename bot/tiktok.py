import re
import asyncio
import tempfile
import os
import yt_dlp
import httpx


TIKTOK_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|m\.)?(tiktok\.com|tiktok\.com/@[\w.-]+/video/\d+)",
)
TIKTOK_SHORT_PATTERN = re.compile(r"https?://(?:vm\.|vt\.)?tiktok\.com/\S+")


def is_tiktok_url(text: str) -> bool:
    return bool(TIKTOK_PATTERN.search(text) or TIKTOK_SHORT_PATTERN.search(text))


async def download_tiktok_video(url: str) -> bytes | None:
    loop = asyncio.get_event_loop()

    def extract():
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best[ext=mp4]/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url"), info.get("title", "video")

    try:
        video_url, title = await loop.run_in_executor(None, extract)
        if not video_url:
            return None
    except Exception:
        return await _fallback_download(url)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(video_url)
        if resp.status_code == 200:
            return resp.content

    return None


async def _fallback_download(url: str) -> bytes | None:
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
            video_url = data["data"]["play"]
            if not video_url:
                video_url = data["data"].get("wmplay")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(video_url)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None
