from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# 設定
# ===============================
TIMEOUT = 8
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# ===============================
# 静的ファイル
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("statics directory not found")

app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def root():
    return FileResponse("statics/index.html")

# ===============================
# Invidious / Poketube インスタンス
# ===============================
INVIDIOUS = {
    "search": [
        "https://pol1.iv.ggtyler.dev",
        "https://youtube.mosesmang.com",
        "https://iteroni.com",
        "https://invidious.0011.lt",
        "https://iv.melmac.space",
        "https://rust.oskamp.nl"
    ],
    "video": [
        "https://invidious.f5.si",
        "https://invidious.exma.de",
        "https://cal1.iv.ggtyler.dev",
        "https://pol1.iv.ggtyler.dev",
        "https://lekker.gay"
    ],
    "comments": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl"
    ],
    # Poketube（DL用）
    "poketube": [
        "https://invid-api.poketube.fun",
        "https://eu-proxy.poketube.fun"
    ]
}

# ===============================
# 共通フェイルオーバー
# ===============================
def fetch_any(instances, path, params=None):
    instances = instances[:]
    random.shuffle(instances)

    for base in instances:
        try:
            r = requests.get(
                base + path,
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT
            )
            if r.status_code == 200:
                return r.json(), base
        except:
            pass

    return None, None

# ===============================
# 検索API
# ===============================
@app.get("/api/search")
def api_search(q: str):
    data, used = fetch_any(
        INVIDIOUS["search"],
        "/api/v1/search",
        {"q": q, "type": "video"}
    )

    if not data:
        raise HTTPException(503, "Search unavailable")

    return {
        "used_instance": used,
        "results": data
    }

# ===============================
# 動画情報API
# ===============================
@app.get("/api/video")
def api_video(video_id: str):
    data, used = fetch_any(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}"
    )

    if not data:
        raise HTTPException(503, "Video info unavailable")

    return {
        "used_instance": used,
        "video": {
            "title": data.get("title"),
            "author": data.get("author"),
            "description": data.get("description"),
            "viewCount": data.get("viewCount"),
            "lengthSeconds": data.get("lengthSeconds"),
            "recommended": data.get("recommendedVideos", [])
        }
    }

# ===============================
# コメントAPI
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str):
    data, used = fetch_any(
        INVIDIOUS["comments"],
        f"/api/v1/comments/{video_id}"
    )

    if not data:
        return {
            "used_instance": None,
            "comments": []
        }

    comments = []
    for c in data.get("comments", []):
        comments.append({
            "author": c.get("author"),
            "content": c.get("content")
        })

    return {
        "used_instance": used,
        "comments": comments
    }

# ===============================
# ダウンロードAPI（最重要）
# Invidious → Poketube 総当たり
# ===============================
@app.get("/api/download")
def api_download(
    video_id: str,
    quality: str = Query("360")
):
    # ---------- Invidious ----------
    instances = INVIDIOUS["video"][:]
    random.shuffle(instances)

    for base in instances:
        try:
            r = requests.get(
                f"{base}/api/v1/videos/{video_id}",
                headers=HEADERS,
                timeout=TIMEOUT
            )
            if r.status_code != 200:
                continue

            data = r.json()
            streams = data.get("formatStreams", [])

            for s in streams:
                if not s.get("url"):
                    continue
                label = str(s.get("qualityLabel", ""))
                if quality in label:
                    return RedirectResponse(
                        s["url"],
                        status_code=302
                    )
        except:
            pass

    # ---------- Poketube ----------
    for base in INVIDIOUS["poketube"]:
        try:
            r = requests.get(
                f"{base}/api/v1/videos/{video_id}",
                headers=HEADERS,
                timeout=TIMEOUT
            )
            if r.status_code != 200:
                continue

            data = r.json()
            streams = data.get("formatStreams", [])

            for s in streams:
                if not s.get("url"):
                    continue
                label = str(s.get("qualityLabel", ""))
                if quality in label:
                    return RedirectResponse(
                        s["url"],
                        status_code=302
                    )
        except:
            pass

    return JSONResponse(
        status_code=503,
        content={"detail": "Download unavailable (all Invidious & Poketube failed)"}
        )
