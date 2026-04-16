from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import shutil
import os

app = FastAPI(title="SaveIt Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

COOKIES_SRC = "/etc/secrets/cookies.txt"
COOKIES_DST = "/tmp/cookies.txt"

def get_cookies_path():
    if os.path.exists(COOKIES_SRC):
        shutil.copy2(COOKIES_SRC, COOKIES_DST)
        return COOKIES_DST
    return None

def detect_platform(url: str) -> str:
    if "instagram.com" in url:
        return "instagram"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "facebook.com" in url or "fb.watch" in url:
        return "facebook"
    return "unknown"

def get_ydl_opts(extra: dict = {}):
    cookies = get_cookies_path()
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # Android client use karo — bot detection bypass
        "extractor_args": {
            "youtube": {
                "player_client": ["android"],
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip",
        },
    }
    if cookies:
        opts["cookiefile"] = cookies
    opts.update(extra)
    return opts

@app.get("/")
def root():
    return {
        "status": "SaveIt API is running 🚀",
        "cookies_found": os.path.exists(COOKIES_SRC)
    }

@app.post("/info")
def get_media_info(req: URLRequest):
    url = req.url.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported URL.")

    ydl_opts = get_ydl_opts()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        if info.get("formats"):
            for f in info["formats"]:
                height = f.get("height")
                ext = f.get("ext", "mp4")
                has_video = f.get("vcodec", "none") != "none"
                has_audio = f.get("acodec", "none") != "none"

                if has_video and has_audio and height:
                    label = f"{height}p {ext.upper()}"
                    if label not in seen:
                        seen.add(label)
                        formats.append({
                            "format_id": f["format_id"],
                            "label": label,
                            "height": height,
                            "ext": ext,
                            "filesize": f.get("filesize"),
                        })

            formats.append({
                "format_id": "bestaudio/best",
                "label": "Audio Only (MP3)",
                "height": 0,
                "ext": "mp3",
                "filesize": None,
            })
            formats = sorted(formats, key=lambda x: x["height"], reverse=True)

        if not formats:
            formats = [{"format_id": "best", "label": "Best Quality", "height": 0, "ext": "mp4", "filesize": None}]

        return {
            "platform": platform,
            "title": info.get("title", "Media"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader") or info.get("channel"),
            "formats": formats,
        }

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        raise HTTPException(status_code=422, detail=f"Could not fetch media: {error_msg[:300]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


@app.get("/download")
def download_media(url: str, format_id: str = "best"):
    url = url.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported URL.")

    if format_id == "bestaudio/best" or format_id == "audio":
        ydl_fmt = "bestaudio/best"
    else:
        ydl_fmt = f"{format_id}+bestaudio/{format_id}/best"

    ydl_opts = get_ydl_opts({"format": ydl_fmt})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        direct_url = info.get("url") or (info.get("formats", [{}])[-1].get("url"))

        if not direct_url:
            raise HTTPException(status_code=404, detail="Could not get download URL.")

        return {
            "download_url": direct_url,
            "title": info.get("title", "media"),
            "ext": info.get("ext", "mp4"),
            "platform": platform,
        }

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=422, detail=str(e)[:300])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])
