from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import re

app = FastAPI(title="SaveIt Downloader API")

# CORS — allow all origins (apna frontend domain daal sakte ho baad mein)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

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
    """Get media info (title, thumbnail, formats) without downloading"""
    url = req.url.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported URL. Only Instagram, YouTube, Facebook supported.")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # Instagram ke liye cookies zaruri ho sakti hain
        # "cookiefile": "cookies.txt",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Formats clean karke bhejte hain
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

            # Audio only option
            formats.append({
                "format_id": "bestaudio/best",
                "label": "Audio Only (MP3)",
                "height": 0,
                "ext": "mp3",
                "filesize": None,
            })

            # Height ke hisaab se sort karo
            formats = sorted(formats, key=lambda x: x["height"], reverse=True)

        # Agar formats empty hain toh best format de do
        if not formats:
            formats = [
                {"format_id": "best", "label": "Best Quality", "height": 0, "ext": "mp4", "filesize": None},
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
        raise HTTPException(status_code=422, detail=f"Could not fetch media: {error_msg[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@app.get("/download")
def download_media(url: str, format_id: str = "best"):
    """
    Returns a direct download URL for the requested format.
    yt-dlp se direct stream URL nikalta hai.
    """
    url = url.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported URL.")

    # Audio only case
    if format_id == "bestaudio/best" or format_id == "audio":
        ydl_fmt = "bestaudio/best"
    else:
        ydl_fmt = f"{format_id}+bestaudio/{format_id}/best"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": ydl_fmt,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Direct stream URL
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
        raise HTTPException(status_code=422, detail=str(e)[:200])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
