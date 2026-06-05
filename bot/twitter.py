import re
import asyncio
import yt_dlp
import httpx


TWITTER_PATTERNS = [
    re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+"),
    re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+\S*"),
]


def is_twitter_url(text: str) -> bool:
    return any(p.search(text) for p in TWITTER_PATTERNS)


async def download_twitter_video(url: str) -> bytes | None:
    loop = asyncio.get_event_loop()

    def extract():
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "best[ext=mp4]/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", [info])
            for entry in entries:
                video_url = entry.get("url")
                if video_url:
                    return video_url, entry.get("title", "video")
            return None, None

    try:
        video_url, _ = await loop.run_in_executor(None, extract)
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
    match = re.search(r"/status/(\d+)", url)
    if not match:
        return None
    tweet_id = match.group(1)
    api_url = f"https://api.vxtwitter.com/Twitter/status/{tweet_id}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(api_url)
            data = resp.json()
            media = data.get("media_extended") or data.get("media")
            if not media:
                return None
            video_url = media[0].get("video_url") or media[0].get("url")
            if not video_url:
                return None

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(video_url)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None
