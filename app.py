from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# Static
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("statics directory not found")

app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def root():
    return FileResponse("statics/index.html")

# ===============================
# API BASE
# ===============================
VIDEO_APIS = [
    "https://iv.melmac.space",
    "https://pol1.iv.ggtyler.dev",
    "https://cal1.iv.ggtyler.dev",
    "https://invidious.0011.lt",
]

PLAYLIST_APIS = [
    "https://invidious.lunivers.trade",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
    "https://iv.melmac.space",
    "https://iv.duti.dev",
]

SEARCH_APIS = [
    "https://api-five-zeta-55.vercel.app"
]

CHANNEL_APIS = [
    "https://invidious.lunivers.trade",
    "https://invid-api.poketube.fun",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
    "https://iv.melmac.space",
    "https://iv.duti.dev",
]

COMMENTS_APIS = [
    "https://invidious.lunivers.trade",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
    "https://iv.duti.dev",
    "https://iv.melmac.space",
]

EDU_STREAM_API_BASE_URL = "https://siawaseok.duckdns.org/api/stream/"
EDU_VIDEO_API_BASE_URL  = "https://siawaseok.duckdns.org/api/video2/"
STREAM_YTDL_API_BASE_URL = "https://yudlp.vercel.app/stream/"
SHORT_STREAM_API_BASE_URL = "https://yt-dl-kappa.vercel.app/short/"

TIMEOUT = 6

# ===============================
# Utils
# ===============================
def try_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ===============================
# Search
# ===============================
@app.get("/api/search")
def api_search(q: str):
    for base in SEARCH_APIS:
        data = try_json(f"{base}/api/search", {"q": q})
        if data:
            return {"results": data, "source": base}
    raise HTTPException(503, "Search unavailable")

# ===============================
# Video Info
# ===============================
@app.get("/api/video")
def api_video(video_id: str):
    random.shuffle(VIDEO_APIS)

    for base in VIDEO_APIS:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if data:
            return {
                "title": data.get("title"),
                "author": data.get("author"),
                "description": data.get("description"),
                "downloadable": True,
                "formats": [
                    {"quality": "360p"},
                    {"quality": "720p"},
                    {"quality": "best"},
                ],
                "source": base
            }

    edu = try_json(f"{EDU_VIDEO_API_BASE_URL}{video_id}")
    if edu:
        return {
            "title": edu.get("title"),
            "author": edu.get("author"),
            "description": edu.get("description"),
            "downloadable": True,
            "formats": edu.get("formats", [{"quality": "auto"}]),
            "source": "edu"
        }

    raise HTTPException(503, "Video info unavailable")

# ===============================
# Comments
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str):
    for base in COMMENTS_APIS:
        data = try_json(f"{base}/api/v1/comments/{video_id}")
        if data:
            return {
                "comments": [
                    {
                        "author": c.get("author"),
                        "content": c.get("content")
                    }
                    for c in data.get("comments", [])
                ],
                "source": base
            }
    return {"comments": [], "source": None}

# ===============================
# Channel
# ===============================
@app.get("/api/channel")
def api_channel(channel_id: str):
    for base in CHANNEL_APIS:
        data = try_json(f"{base}/api/v1/channels/{channel_id}")
        if data:
            return data
    raise HTTPException(503, "Channel unavailable")

# ===============================
# Playlist
# ===============================
@app.get("/api/playlist")
def api_playlist(playlist_id: str):
    for base in PLAYLIST_APIS:
        data = try_json(f"{base}/api/v1/playlists/{playlist_id}")
        if data:
            return data
    raise HTTPException(503, "Playlist unavailable")

# ===============================
# Download / Stream
# ===============================
@app.get("/api/download")
def api_download(video_id: str, quality: str = "best"):
    for url in [
        EDU_STREAM_API_BASE_URL,
        STREAM_YTDL_API_BASE_URL,
        SHORT_STREAM_API_BASE_URL
    ]:
        data = try_json(f"{url}{video_id}", {"quality": quality})
        if data and data.get("url"):
            return RedirectResponse(data["url"])

    for base in VIDEO_APIS:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue
        for f in data.get("adaptiveFormats", []):
            if quality in (f.get("qualityLabel") or "") and f.get("url"):
                return RedirectResponse(f["url"])

    raise HTTPException(
        503,
        "Download unavailable (all Invidious / EDU / yt-dlp failed)"
        )
