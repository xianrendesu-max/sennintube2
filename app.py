from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# Static
# ===============================
if not os.path.isdir("statics"):
    os.makedirs("statics")

app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def root():
    return FileResponse("statics/index.html")

# ===============================
# API BASE LIST
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
    "https://api-five-zeta-55.vercel.app",
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

TIMEOUT = 7
UA = {"User-Agent": "Mozilla/5.0"}

# ===============================
# Utils
# ===============================
def try_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT, headers=UA)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ===============================
# Search（総当たり）
# ===============================
@app.get("/api/search")
def api_search(q: str = Query(...)):
    apis = SEARCH_APIS[:]
    random.shuffle(apis)

    for base in apis:
        data = try_json(f"{base}/api/search", {"q": q})
        if data:
            return {
                "results": data,
                "source": base
            }

    raise HTTPException(503, "Search unavailable (all APIs failed)")

# ===============================
# Video Info（総当たり）
# ===============================
@app.get("/api/video")
def api_video(video_id: str = Query(...)):
    apis = VIDEO_APIS[:]
    random.shuffle(apis)

    for base in apis:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue

        formats = []
        for f in data.get("adaptiveFormats", []):
            if f.get("qualityLabel"):
                formats.append({
                    "quality": f.get("qualityLabel")
                })

        return {
            "title": data.get("title"),
            "author": data.get("author"),
            "description": data.get("description"),
            "viewCount": data.get("viewCount"),
            "lengthSeconds": data.get("lengthSeconds"),
            "formats": formats or [{"quality": "auto"}],
            "source": base,
            "downloadable": True
        }

    # EDU fallback
    edu = try_json(f"{EDU_VIDEO_API_BASE_URL}{video_id}")
    if edu:
        return {
            "title": edu.get("title"),
            "author": edu.get("author"),
            "description": edu.get("description"),
            "formats": edu.get("formats", [{"quality": "auto"}]),
            "source": "edu",
            "downloadable": True
        }

    raise HTTPException(503, "Video info unavailable (all sources failed)")

# ===============================
# Comments（総当たり）
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str = Query(...)):
    apis = COMMENTS_APIS[:]
    random.shuffle(apis)

    for base in apis:
        data = try_json(f"{base}/api/v1/comments/{video_id}")
        if not data:
            continue

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
# Channel（総当たり）
# ===============================
@app.get("/api/channel")
def api_channel(channel_id: str = Query(...)):
    apis = CHANNEL_APIS[:]
    random.shuffle(apis)

    for base in apis:
        data = try_json(f"{base}/api/v1/channels/{channel_id}")
        if data:
            return data

    raise HTTPException(503, "Channel unavailable")

# ===============================
# Playlist（総当たり）
# ===============================
@app.get("/api/playlist")
def api_playlist(playlist_id: str = Query(...)):
    apis = PLAYLIST_APIS[:]
    random.shuffle(apis)

    for base in apis:
        data = try_json(f"{base}/api/v1/playlists/{playlist_id}")
        if data:
            return data

    raise HTTPException(503, "Playlist unavailable")

# ===============================
# Download / Stream（完全総当たり）
# ===============================
@app.get("/api/download")
def api_download(video_id: str, quality: str = "best"):
    stream_apis = [
        EDU_STREAM_API_BASE_URL,
        STREAM_YTDL_API_BASE_URL,
        SHORT_STREAM_API_BASE_URL,
    ]
    random.shuffle(stream_apis)

    # 外部ストリームAPI
    for base in stream_apis:
        data = try_json(f"{base}{video_id}", {"quality": quality})
        if data and data.get("url"):
            return RedirectResponse(data["url"])

    # Invidious 直URL
    apis = VIDEO_APIS[:]
    random.shuffle(apis)

    for base in apis:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue

        for f in data.get("adaptiveFormats", []):
            q = f.get("qualityLabel", "")
            if quality == "best" or quality in q:
                if f.get("url"):
                    return RedirectResponse(f["url"])

    raise HTTPException(
        503,
        "Download unavailable (all Invidious / EDU / yt-dlp failed)"
)
