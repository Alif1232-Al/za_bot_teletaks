import re
import httpx


TWITTER_PATTERNS = [
    re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+"),
    re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+\S*"),
]


def is_twitter_url(text: str) -> bool:
    return any(p.search(text) for p in TWITTER_PATTERNS)


async def get_twitter_video_url(url: str) -> str | None:
    match = re.search(r"/status/(\d+)", url)
    if not match:
        return None
    tweet_id = match.group(1)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.vxtwitter.com/Twitter/status/{tweet_id}"
            )
            data = resp.json()
            media = data.get("media_extended") or data.get("media")
            if not media:
                return None
            return media[0].get("video_url") or media[0].get("url")
    except Exception:
        return await _ytdlp_get_url(url, tweet_id)


async def _ytdlp_get_url(url: str, tweet_id: str | None = None) -> str | None:
    import asyncio
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
            entries = info.get("entries", [info])
            for entry in entries:
                video_url = entry.get("url")
                if video_url:
                    return video_url
            return None

    try:
        return await loop.run_in_executor(None, extract)
    except Exception:
        return None
