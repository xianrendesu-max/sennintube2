from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# Static
# ===============================
# Render で statics が無くても即死しないようにする
if os.path.isdir("statics"):
    app.mount("/static", StaticFiles(directory="statics"), name="static")
else:
    print("⚠ statics directory not found (skipped mount)")

@app.get("/")
def root():
    if os.path.isfile("statics/index.html"):
        return FileResponse("statics/index.html")
    return {"status": "index.html not found"}

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

SEARCH_APIS = VIDEO_APIS

COMMENTS_APIS = [
    "https://invidious.lunivers.trade",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
    "https://iv.melmac.space",
    "https://iv.duti.dev",
]

EDU_STREAM_API_BASE_URL = "https://raw.githubusercontent.com/toka-kun/Education/refs/heads/main/keys/key1.json"
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
    except Exception as e:
        print("request error:", e)
    return None

# ===============================
# Search
# ===============================
@app.get("/api/search")
def api_search(q: str):
    results = []
    random.shuffle(SEARCH_APIS)

    for base in SEARCH_APIS:
        data = try_json(f"{base}/api/v1/search", {"q": q, "type": "video"})
        if not isinstance(data, list):
            continue

        for v in data:
            if not v.get("videoId"):
                continue

            results.append({
                "videoId": v.get("videoId"),
                "title": v.get("title"),
                "author": v.get("author"),
                "authorId": v.get("authorId"),
            })

        if results:
            return {
                "count": len(results),
                "results": results,
                "source": base
            }

    raise HTTPException(status_code=503, detail="Search unavailable")

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
                "viewCount": data.get("viewCount"),
                "lengthSeconds": data.get("lengthSeconds"),
                "source": base
            }

    raise HTTPException(status_code=503, detail="Video info unavailable")

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
def api_channel(c: str):
    random.shuffle(VIDEO_APIS)

    for base in VIDEO_APIS:
        ch = try_json(f"{base}/api/v1/channels/{c}")
        if not ch:
            continue

        # ===============================
        # 動画一覧（並び替え対応）
        # ===============================
        latest_videos = []
        for v in ch.get("latestVideos", []):
            published_raw = v.get("published")
            published_iso = None

            if published_raw:
                try:
                    published_iso = published_raw.replace("Z", "+00:00")
                except:
                    published_iso = None

            latest_videos.append({
                "videoId": v.get("videoId"),
                "title": v.get("title"),
                "author": ch.get("author"),
                "authorId": c,
                "viewCount": v.get("viewCount"),
                "viewCountText": v.get("viewCountText"),
                "published": published_iso,
                "publishedText": v.get("publishedText")
            })

        # ===============================
        # 関連チャンネル
        # ===============================
        related_channels = []
        for r in ch.get("relatedChannels", []):
            related_channels.append({
                "channelId": r.get("authorId"),
                "name": r.get("author"),
                "icon": (
                    r.get("authorThumbnails", [{}])[-1].get("url")
                    if r.get("authorThumbnails") else None
                ),
                "subCountText": r.get("subCountText")
            })

        # ===============================
        # フロント向け整形レスポンス
        # ===============================
        return {
            "author": ch.get("author"),
            "authorId": c,
            "authorThumbnails": ch.get("authorThumbnails"),
            "description": ch.get("description"),
            "subCount": ch.get("subCount"),
            "viewCount": ch.get("viewCount"),
            "videoCount": ch.get("videoCount"),
            "joinedDate": ch.get("joinedDate"),
            "latestVideos": latest_videos,
            "relatedChannels": related_channels,
            "source": base
        }

    raise HTTPException(status_code=503, detail="Channel unavailable")
# ===============================
# Stream URL ONLY（日本語音声優先）
# ===============================
@app.get("/api/streamurl")
def api_streamurl(video_id: str, quality: str = "best"):
    # ① yt-dlp / proxy 系
    for base in [
        EDU_STREAM_API_BASE_URL,
        STREAM_YTDL_API_BASE_URL,
        SHORT_STREAM_API_BASE_URL
    ]:
        data = try_json(f"{base}{video_id}", {"quality": quality})
        if data and data.get("url"):
            return RedirectResponse(data["url"])

    # ② Invidious fallback（英語音声除外）
    for base in VIDEO_APIS:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue

        for f in data.get("adaptiveFormats", []):
            if not f.get("url"):
                continue

            lang = (f.get("language") or "").lower()
            audio_track = str(f.get("audioTrack") or "").lower()

            if "en" in lang:
                continue
            if "english" in audio_track:
                continue

            label = f.get("qualityLabel") or ""

            if quality == "best" or quality in label:
                return RedirectResponse(f["url"])

    raise HTTPException(status_code=503, detail="Stream unavailable")
