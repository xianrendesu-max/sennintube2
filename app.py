from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import random

app = FastAPI()

# ===============================
# Invidious インスタンス（複数）
# ===============================
INVIDIOUS_INSTANCES = [
    "https://pol1.iv.ggtyler.dev",
    "https://vid.puffyan.us",
    "https://invidious.snopyta.org",
]

def pick_instance():
    return random.choice(INVIDIOUS_INSTANCES)

# ===============================
# 静的HTML配信
# ===============================
app.mount("/", StaticFiles(directory="statics", html=True), name="static")

# ===============================
# 検索
# ===============================
@app.get("/api/search")
def search(q: str):
    inst = pick_instance()
    try:
        r = requests.get(
            f"{inst}/api/v1/search",
            params={"q": q, "type": "video"},
            timeout=10
        )
        r.raise_for_status()
        return {
            "used_instance": inst,
            "results": r.json()
        }
    except Exception:
        raise HTTPException(status_code=500, detail="search failed")

# ===============================
# 動画情報 + 関連動画
# ===============================
@app.get("/api/video/{video_id}")
def video(video_id: str):
    inst = pick_instance()
    try:
        r = requests.get(
            f"{inst}/api/v1/videos/{video_id}",
            timeout=10
        )
        r.raise_for_status()
        data = r.json()

        return {
            "video": {
                "title": data.get("title"),
                "description_html": data.get("descriptionHtml"),
                "author": data.get("author"),
                "view_count": data.get("viewCount"),
            },
            "related": data.get("recommendedVideos", [])
        }
    except Exception:
        raise HTTPException(status_code=500, detail="video failed")

# ===============================
# コメント
# ===============================
@app.get("/api/comments/{video_id}")
def comments(video_id: str):
    inst = pick_instance()
    try:
        r = requests.get(
            f"{inst}/api/v1/comments/{video_id}",
            timeout=10
        )
        r.raise_for_status()
        return {
            "comments": r.json().get("comments", [])
        }
    except Exception:
        raise HTTPException(status_code=500, detail="comments failed")

# ===============================
# ダウンロードURL取得
# ===============================
@app.get("/api/download/{video_id}")
def download(video_id: str):
    inst = pick_instance()
    try:
        r = requests.get(
            f"{inst}/api/v1/videos/{video_id}",
            timeout=10
        )
        r.raise_for_status()
        data = r.json()

        formats = []

        for f in data.get("adaptiveFormats", []):
            if f.get("url"):
                formats.append({
                    "url": f["url"],
                    "ext": f.get("container"),
                    "quality": f.get("qualityLabel")
                })

        return {"formats": formats}
    except Exception:
        raise HTTPException(status_code=500, detail="download failed")

# ===============================
# education用ダミーembed
# ===============================
@app.get("/api/edu/{video_id}")
def education(video_id: str):
    return JSONResponse({
        "embed": f"https://www.youtubeeducation.com/embed/{video_id}"
    })
