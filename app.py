from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# Invidious instances
# ===============================
INVIDIOUS = [
    "https://pol1.iv.ggtyler.dev",
    "https://vid.puffyan.us",
    "https://invidious.snopyta.org",
]

def pick():
    return random.choice(INVIDIOUS)

# ===============================
# Static files
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("Directory 'statics' does not exist")

app.mount("/", StaticFiles(directory="statics", html=True), name="static")

# ===============================
# Search
# ===============================
@app.get("/api/search")
def search(q: str):
    inst = pick()
    r = requests.get(
        f"{inst}/api/v1/search",
        params={"q": q, "type": "video"},
        timeout=10
    )
    r.raise_for_status()
    return {"results": r.json(), "used_instance": inst}

# ===============================
# Trending
# ===============================
@app.get("/api/trending")
def trending(region: str = "JP"):
    inst = pick()
    r = requests.get(
        f"{inst}/api/v1/trending",
        params={"region": region},
        timeout=10
    )
    r.raise_for_status()
    return {"results": r.json()}

# ===============================
# Video + related
# ===============================
@app.get("/api/video/{video_id}")
def video(video_id: str):
    inst = pick()
    r = requests.get(f"{inst}/api/v1/videos/{video_id}", timeout=10)
    r.raise_for_status()
    d = r.json()
    return {
        "title": d.get("title"),
        "description": d.get("description"),
        "related": d.get("recommendedVideos", [])
    }

# ===============================
# Comments
# ===============================
@app.get("/api/comments/{video_id}")
def comments(video_id: str):
    inst = pick()
    r = requests.get(f"{inst}/api/v1/comments/{video_id}", timeout=10)
    r.raise_for_status()
    return {"comments": r.json().get("comments", [])}

# ===============================
# 360p download (itag18)
# ===============================
@app.get("/api/download/360p/{video_id}")
def download_360p(video_id: str):
    inst = pick()
    r = requests.get(f"{inst}/api/v1/videos/{video_id}", timeout=10)
    r.raise_for_status()
    d = r.json()

    for f in d.get("adaptiveFormats", []):
        if f.get("itag") == "18" and f.get("url"):
            return {"url": f["url"]}

    raise HTTPException(status_code=404, detail="360p not found")

# ===============================
# m3u8 (highest)
# ===============================
@app.get("/api/download/m3u8/{video_id}")
def download_m3u8(video_id: str):
    inst = pick()
    r = requests.get(f"{inst}/api/v1/videos/{video_id}", timeout=10)
    r.raise_for_status()
    d = r.json()

    streams = [
        f for f in d.get("adaptiveFormats", [])
        if f.get("type","").startswith("video") and f.get("url")
    ]
    if not streams:
        raise HTTPException(status_code=404, detail="m3u8 not found")

    return {"url": streams[0]["url"]}
