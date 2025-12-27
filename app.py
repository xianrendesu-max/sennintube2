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
# API BASE LIST
# ===============================
VIDEO_APIS = [
    "https://iv.melmac.space",
    "https://pol1.iv.ggtyler.dev",
    "https://cal1.iv.ggtyler.dev",
    "https://invidious.0011.lt",
    "https://yt.omada.cafe",
]

SEARCH_APIS = [
    "https://pol1.iv.ggtyler.dev",
    "https://cal1.iv.ggtyler.dev",
    "https://iv.melmac.space",
    "https://invidious.0011.lt",
    "https://yt.omada.cafe",
]

CHANNEL_APIS = [
    "https://invidious.lunivers.trade",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
    "https://iv.melmac.space",
    "https://iv.duti.dev",
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

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ===============================
# Utils
# ===============================
def try_json(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ===============================
# Search（総当たり＋正規化）
# ===============================
@app.get("/api/search")
def api_search(q: str):
    results = []

    random.shuffle(SEARCH_APIS)
    for base in SEARCH_APIS:
        data = try_json(
            f"{base}/api/v1/search",
            {"q": q, "type": "video"}
        )
        if not isinstance(data, list):
            continue

        for v in data:
            if not v.get("videoId"):
                continue
            results.append({
                "videoId": v["videoId"],
                "title": v.get("title"),
                "author": v.get("author"),
            })

        if results:
            return {
                "results": results,
                "source": base
            }

    # 補助API
    data = try_json("https://api-five-zeta-55.vercel.app/api/search", {"q": q})
    if data:
        for v in data.get("videos", []):
            results.append({
                "videoId": v.get("id"),
                "title": v.get("title"),
                "author": v.get("author"),
            })

        if results:
            return {
                "results": results,
                "source": "api-five-zeta-55"
            }

    raise HTTPException(503, "Search unavailable (all instances failed)")

# ===============================
# Video Info（総当たり）
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
                "viewCount": data.get("viewCount"),
                "lengthSeconds": data.get("lengthSeconds"),
                "source": base
            }

    edu = try_json(f"{EDU_VIDEO_API_BASE_URL}{video_id}")
    if edu:
        return {
            "title": edu.get("title"),
            "author": edu.get("author"),
            "description": edu.get("description"),
            "viewCount": edu.get("viewCount"),
            "lengthSeconds": edu.get("lengthSeconds"),
            "source": "edu"
        }

    raise HTTPException(503, "Video info unavailable")

# ===============================
# Comments（総当たり）
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
# Download / Stream（総当たり）
# ===============================
@app.get("/api/download")
def api_download(video_id: str, quality: str = "best"):
    # EDU / yt-dlp proxy
    for base in [
        EDU_STREAM_API_BASE_URL,
        STREAM_YTDL_API_BASE_URL,
        SHORT_STREAM_API_BASE_URL
    ]:
        data = try_json(f"{base}{video_id}", {"quality": quality})
        if data and data.get("url"):
            return RedirectResponse(data["url"])

    # Invidious adaptiveFormats
    for base in VIDEO_APIS:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue

        for f in data.get("adaptiveFormats", []):
            if not f.get("url"):
                continue
            label = f.get("qualityLabel") or ""
            if quality == "best" or quality in label:
                return RedirectResponse(f["url"])

    raise HTTPException(
        503,
        "Download unavailable (all Invidious / EDU / yt-dlp failed)"
            )
