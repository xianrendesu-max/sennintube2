from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# Invidious インスタンス定義
# ===============================
INVIDIOUS = {
    "search": [
        "https://pol1.iv.ggtyler.dev/",
        "https://youtube.mosesmang.com/",
        "https://iteroni.com/",
        "https://invidious.0011.lt/",
        "https://iv.melmac.space/",
        "https://rust.oskamp.nl/"
    ],
    "video": [
        "https://invidious.exma.de/",
        "https://invidious.f5.si/",
        "https://siawaseok-wakame-server2.glitch.me/",
        "https://lekker.gay/",
        "https://id.420129.xyz/",
        "https://invid-api.poketube.fun/",
        "https://eu-proxy.poketube.fun/",
        "https://cal1.iv.ggtyler.dev/",
        "https://pol1.iv.ggtyler.dev/"
    ],
    "comments": [
        "https://siawaseok-wakame-server2.glitch.me/",
        "https://invidious.0011.lt/",
        "https://invidious.nietzospannend.nl/"
    ]
}

# ===============================
# フェイルオーバー付き GET
# ===============================
def fetch_with_failover(instances, path, params=None):
    last_error = None
    for base in instances:
        try:
            url = base.rstrip("/") + path
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json(), base
        except Exception as e:
            last_error = e
            continue
    raise HTTPException(status_code=503, detail=f"All Invidious instances failed: {last_error}")

# ===============================
# API : 検索
# ===============================
@app.get("/api/search")
def api_search(q: str):
    data, used = fetch_with_failover(
        INVIDIOUS["search"],
        "/api/v1/search",
        {"q": q, "type": "video"}
    )
    return {
        "results": data,
        "used_instance": used
    }

# ===============================
# API : 動画情報 + 関連
# ===============================
@app.get("/api/video")
def api_video(video_id: str):
    data, used = fetch_with_failover(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}"
    )
    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "author": data.get("author"),
        "viewCount": data.get("viewCount"),
        "recommended": data.get("recommendedVideos", []),
        "used_instance": used
    }

# ===============================
# API : コメント
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str):
    data, used = fetch_with_failover(
        INVIDIOUS["comments"],
        f"/api/v1/comments/{video_id}"
    )
    return data

# ===============================
# API : ダウンロード (360p / m3u8)
# ===============================
@app.get("/api/download")
def api_download(video_id: str):
    data, used = fetch_with_failover(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}"
    )

    formats = []
    for f in data.get("adaptiveFormats", []):
        if not f.get("url"):
            continue

        # 360p
        if f.get("itag") == "18":
            formats.append({
                "quality": "360p",
                "type": "mp4",
                "url": f["url"]
            })

        # m3u8
        if "m3u8" in f.get("type", ""):
            formats.append({
                "quality": f.get("qualityLabel", "auto"),
                "type": "m3u8",
                "url": f["url"]
            })

    if not formats:
        raise HTTPException(status_code=404, detail="No downloadable formats found")

    return {
        "formats": formats,
        "used_instance": used
    }

# ===============================
# 静的ファイル
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("statics directory not found")

app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def index():
    return FileResponse("statics/index.html")
