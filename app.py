from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import requests
import subprocess
import os

app = FastAPI()

# ===============================
# Invidious インスタンス定義（安定重視）
# ===============================
INVIDIOUS = {
    "search": [
        "https://pol1.iv.ggtyler.dev",
        "https://iv.melmac.space",
        "https://invidious.0011.lt",
        "https://iteroni.com"
    ],
    "video": [
        "https://pol1.iv.ggtyler.dev",
        "https://cal1.iv.ggtyler.dev",
        "https://invidious.exma.de",
        "https://lekker.gay"
    ],
    "comments": [
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl"
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
            r = requests.get(
                url,
                params=params,
                timeout=6,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code != 200:
                last_error = f"{base} HTTP {r.status_code}"
                continue
            return r.json(), base
        except Exception as e:
            last_error = str(e)
            continue

    raise HTTPException(
        status_code=503,
        detail="Invidious unavailable (all instances failed)"
    )

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
# API : 動画情報 + 関連動画
# ===============================
@app.get("/api/video/{video_id}")
def api_video(video_id: str):
    data, used = fetch_with_failover(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}"
    )
    return {
        "video": data,
        "related": data.get("recommendedVideos", []),
        "used_instance": used
    }

# ===============================
# API : コメント
# ===============================
@app.get("/api/comments/{video_id}")
def api_comments(video_id: str):
    data, used = fetch_with_failover(
        INVIDIOUS["comments"],
        f"/api/v1/comments/{video_id}"
    )
    return data

# ===============================
# API : Invidious ダウンロード（補助）
# ===============================
@app.get("/api/download/{video_id}")
def api_download(video_id: str, itag: str):
    data, used = fetch_with_failover(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}"
    )

    for f in data.get("adaptiveFormats", []):
        if f.get("itag") == itag and f.get("url"):
            return {
                "url": f["url"],
                "used_instance": used
            }

    raise HTTPException(status_code=404, detail="Format not found")

# ===============================
# API : yt-dlp プロキシ（最終手段・超安定）
# ===============================
@app.get("/api/dlp/{video_id}")
def dlp_proxy(video_id: str, itag: str = "18"):
    if itag == "18":
        fmt = "best[height<=360]/best"
    elif itag == "22":
        fmt = "best[height<=720]/best"
    else:
        fmt = "best"

    cmd = [
        "yt-dlp",
        "-f", fmt,
        "-o", "-",
        f"https://www.youtube.com/watch?v={video_id}"
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="yt-dlp is not installed"
        )

    return StreamingResponse(
        proc.stdout,
        media_type="video/mp4"
    )

# ===============================
# 静的ファイル
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("statics directory not found")

app.mount("/static", StaticFiles(directory="statics"), name="static")

# ===============================
# ルート
# ===============================
@app.get("/")
def root():
    return FileResponse("statics/index.html")
