from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
import os
import random

app = FastAPI()

# ===============================
# Static
# ===============================
if not os.path.isdir("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/watch.html")


# ===============================
# Invidious / Poketube / Proxy
# ===============================
INSTANCES = [
    # 追加指定分
    "https://api-five-zeta-55.vercel.app",
    "https://invidious.lunivers.trade",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
    "https://iv.melmac.space",
    "https://iv.duti.dev",

    # 既存安定系
    "https://pol1.iv.ggtyler.dev",
    "https://cal1.iv.ggtyler.dev",
    "https://invidious.0011.lt",
    "https://invidious.f5.si",
    "https://invidious.exma.de",
    "https://invid-api.poketube.fun",
    "https://eu-proxy.poketube.fun"
]

TIMEOUT = 6
UA = {"User-Agent": "Mozilla/5.0"}


# ===============================
# 共通フェイルオーバー
# ===============================
def fetch_video_any(video_id: str):
    instances = INSTANCES[:]
    random.shuffle(instances)

    for base in instances:
        try:
            r = requests.get(
                f"{base}/api/v1/videos/{video_id}",
                timeout=TIMEOUT,
                headers=UA
            )
            if r.status_code == 200:
                return r.json(), base
        except:
            continue

    return None, None


# ===============================
# DL可否 事前判定 API
# ===============================
@app.get("/api/check")
def api_check(video_id: str = Query(...)):
    data, used = fetch_video_any(video_id)

    if not data:
        return {
            "available": False,
            "reason": "Video unavailable on all instances"
        }

    streams = data.get("formatStreams", [])
    downloadable = any(s.get("url") for s in streams)

    return {
        "available": True,
        "downloadable": downloadable,
        "title": data.get("title"),
        "author": data.get("author"),
        "used_instance": used
    }


# ===============================
# 動画情報 + DL一覧
# ===============================
@app.get("/api/video")
def api_video(video_id: str = Query(...)):
    data, used = fetch_video_any(video_id)

    if not data:
        raise HTTPException(503, "Invidious unavailable (all instances failed)")

    formats = []
    for s in data.get("formatStreams", []):
        if s.get("url"):
            formats.append({
                "quality": s.get("qualityLabel", "unknown"),
                "mime": s.get("mimeType"),
                "url": s.get("url")
            })

    return {
        "title": data.get("title"),
        "author": data.get("author"),
        "description": data.get("description"),
        "downloadable": len(formats) > 0,
        "formats": formats,
        "used_instance": used
    }


# ===============================
# ダウンロード（総当たり）
# ===============================
@app.get("/api/download")
def api_download(
    video_id: str = Query(...),
    quality: str = Query(...)
):
    data, used = fetch_video_any(video_id)

    if not data:
        raise HTTPException(503, "Download unavailable (all instances failed)")

    for s in data.get("formatStreams", []):
        if s.get("qualityLabel") == quality and s.get("url"):
            return RedirectResponse(
                url=s["url"],
                status_code=302
            )

    raise HTTPException(404, "No download URL")
