from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import shutil
import os

app = FastAPI(title="SaveIt Downloader API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

# Render Secret File read-only hoti hai — /tmp mein copy karo
COOKIES_SRC = "/etc/secrets/cookies.txt"
COOKIES_DST = "/tmp/cookies.txt"

def get_cookies_path():
    """Cookies ko /tmp mein copy karo (writable location)"""
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

@app.get("/")
def root():
    return {"status": "SaveIt API is running 🚀"}

@app.post("/info")
def get_media_info(req: URLRequest):
    url = req.url.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Only Instagram, YouTube, Facebook supported."
        )

    cookies = get_cookies_path()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies

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

                # Sirf video hona enough hai; YouTube me audio alag stream me hoti hai
                if has_video and height:
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

            # Audio option
            formats.append({
                "format_id": "bestaudio/best",
                "label": "Audio Only",
                "height": 0,
                "ext": "m4a",
                "filesize": None,
            })

            formats = sorted(formats, key=lambda x: x["height"], reverse=True)

        if not formats:
            formats = [
                {
                    "format_id": "best",
                    "label": "Best Quality",
                    "height": 0,
                    "ext": "mp4",
                    "filesize": None,
                }
            ]

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
        if "Private" in error_msg or "login" in error_msg.lower():
            raise HTTPException(status_code=403, detail="Private content — login required.")
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=403, detail="YouTube is asking for login/cookies verification.")
        raise HTTPException(status_code=422, detail=f"Could not fetch media: {error_msg[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

@app.get("/download")
def download_media(url: str, format_id: str = "best"):
    url = url.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported URL.")

    # Safer format handling
    if format_id in ("bestaudio/best", "audio"):
        ydl_fmt = "bestaudio/best"
    elif format_id == "best":
        ydl_fmt = "bestvideo*+bestaudio/best"
    else:
        ydl_fmt = f"{format_id}+bestaudio/best/{format_id}/best"

    cookies = get_cookies_path()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "format": ydl_fmt,
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        direct_url = info.get("url")

        if not direct_url and info.get("requested_formats"):
            for f in info["requested_formats"]:
                if f.get("url"):
                    direct_url = f["url"]
                    break

        if not direct_url and info.get("formats"):
            for f in reversed(info["formats"]):
                if f.get("url"):
                    direct_url = f["url"]
                    break

        if not direct_url:
            raise HTTPException(status_code=404, detail="Could not get download URL.")

        return {
            "download_url": direct_url,
            "title": info.get("title", "media"),
            "ext": info.get("ext", "mp4"),
            "platform": platform,
        }

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "confirm you’re not a bot" in error_msg.lower() or "confirm you're not a bot" in error_msg.lower():
            raise HTTPException(status_code=403, detail="YouTube is asking for login/cookies verification.")
        raise HTTPException(status_code=422, detail=error_msg[:200])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
