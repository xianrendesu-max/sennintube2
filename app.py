from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import subprocess
import json
import random
import os

app = FastAPI()

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
# Invidious インスタンス
# ===============================
INVIDIOUS = {
    "search": [
        "https://pol1.iv.ggtyler.dev",
        "https://iv.melmac.space",
        "https://invidious.0011.lt"
    ],
    "video": [
        "https://pol1.iv.ggtyler.dev",
        "https://cal1.iv.ggtyler.dev",
        "https://iv.melmac.space",
        "https://invidious.0011.lt"
    ],
    "comments": [
        "https://pol1.iv.ggtyler.dev",
        "https://invidious.0011.lt"
    ]
}

TIMEOUT = 6


# ===============================
# フェイルオーバー取得
# ===============================
def fetch_any(instances, path, params=None):
    random.shuffle(instances)
    last_error = None

    for base in instances:
        try:
            r = requests.get(
                base + path,
                params=params,
                timeout=TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code == 200:
                return r.json(), base
        except Exception as e:
            last_error = e
            continue

    return None, last_error


# ===============================
# 🔍 検索 API（← これが無かった）
# ===============================
@app.get("/api/search")
def api_search(q: str = Query(...)):
    data, err = fetch_any(
        INVIDIOUS["search"],
        "/api/v1/search",
        {"q": q, "type": "video"}
    )

    if not data:
        raise HTTPException(
            status_code=503,
            detail=f"Invidious search unavailable: {err}"
        )

    return {
        "results": data,
        "source": "invidious"
    }


# ===============================
# 🎬 動画情報 API
# ===============================
@app.get("/api/video")
def api_video(video_id: str = Query(...)):
    # --- Invidious ---
    data, used = fetch_any(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}"
    )

    if data:
        return {
            "source": "invidious",
            "used_instance": used,
            "video": {
                "title": data.get("title"),
                "author": data.get("author"),
                "description": data.get("description"),
                "viewCount": data.get("viewCount"),
                "lengthSeconds": data.get("lengthSeconds")
            }
        }

    # --- yt-dlp fallback ---
    try:
        cmd = [
            "yt-dlp",
            "-J",
            "--no-warnings",
            "--no-playlist",
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        info = json.loads(p.stdout)

        return {
            "source": "yt-dlp",
            "used_instance": "local yt-dlp",
            "video": {
                "title": info.get("title"),
                "author": info.get("uploader"),
                "description": info.get("description"),
                "viewCount": info.get("view_count"),
                "lengthSeconds": info.get("duration")
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Invidious & yt-dlp unavailable: {e}"
        )


# ===============================
# 💬 コメント API
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str = Query(...)):
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
