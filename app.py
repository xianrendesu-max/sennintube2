from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import subprocess
import json
import os

# ===============================
# App
# ===============================
app = FastAPI()

# ===============================
# Static
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("Directory 'statics' does not exist")

app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def root():
    return FileResponse("statics/index.html")

# ===============================
# Settings
# ===============================
TIMEOUT = 7
HEADERS = {"User-Agent": "Mozilla/5.0"}

INVIDIOUS = {
    "video": [
        "https://invidious.exma.de",
        "https://invidious.f5.si",
        "https://siawaseok-wakame-server2.glitch.me",
        "https://lekker.gay",
        "https://id.420129.xyz",
        "https://invid-api.poketube.fun",
        "https://eu-proxy.poketube.fun",
        "https://cal1.iv.ggtyler.dev",
        "https://pol1.iv.ggtyler.dev",
    ],
    "search": [
        "https://pol1.iv.ggtyler.dev",
        "https://youtube.mosesmang.com",
        "https://iteroni.com",
        "https://invidious.0011.lt",
        "https://iv.melmac.space",
        "https://rust.oskamp.nl",
    ],
    "channel": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://id.420129.xyz",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
    ],
    "playlist": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
        "https://youtube.mosesmang.com",
        "https://iv.melmac.space",
        "https://lekker.gay",
    ],
    "comments": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
    ],
}

# ===============================
# Utils
# ===============================
def fetch_any(instances, path, params=None):
    bases = instances[:]
    random.shuffle(bases)
    for base in bases:
        try:
            r = requests.get(
                base + path,
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                return r.json(), base
        except:
            pass
    return None, None

# ===============================
# Search
# ===============================
@app.get("/api/search")
def api_search(q: str = Query(...)):
    data, used = fetch_any(
        INVIDIOUS["search"],
        "/api/v1/search",
        params={"q": q, "type": "video"},
    )
    if not data:
        raise HTTPException(503, "Invidious unavailable (search)")

    results = []
    for v in data:
        results.append({
            "videoId": v.get("videoId"),
            "title": v.get("title"),
            "author": v.get("author"),
            "lengthSeconds": v.get("lengthSeconds"),
        })

    return {
        "used_instance": used,
        "results": results,
    }

# ===============================
# Video info + related
# ===============================
@app.get("/api/video")
def api_video(video_id: str = Query(...)):
    data, used = fetch_any(
        INVIDIOUS["video"],
        f"/api/v1/videos/{video_id}",
    )
    if not data:
        raise HTTPException(503, "Invidious unavailable (video)")

    related = []
    for r in data.get("recommendedVideos", []):
        related.append({
            "videoId": r.get("videoId"),
            "title": r.get("title"),
            "author": r.get("author"),
        })

    return {
        "used_instance": used,
        "video": {
            "title": data.get("title"),
            "author": data.get("author"),
            "description": data.get("description"),
            "viewCount": data.get("viewCount"),
            "lengthSeconds": data.get("lengthSeconds"),
        },
        "streams": data.get("formatStreams", []),
        "related": related,
    }

# ===============================
# Comments
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str = Query(...)):
    data, used = fetch_any(
        INVIDIOUS["comments"],
        f"/api/v1/comments/{video_id}",
    )
    if not data:
        return {"used_instance": None, "comments": []}

    comments = []
    for c in data.get("comments", []):
        comments.append({
            "author": c.get("author"),
            "content": c.get("content"),
        })

    return {
        "used_instance": used,
        "comments": comments,
    }

# ===============================
# Download (quality selectable)
# ===============================
@app.get("/api/download")
def api_download(video_id: str, quality: str = "360"):
    # ---- 1) Invidious stream 総当たり ----
    instances = INVIDIOUS["video"][:]
    random.shuffle(instances)

    for base in instances:
        try:
            r = requests.get(
                f"{base}/api/v1/videos/{video_id}",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            if r.status_code != 200:
                continue

            data = r.json()
            streams = data.get("formatStreams", [])

            # audio
            if quality == "audio":
                for s in streams:
                    if s.get("audioQuality") and s.get("url"):
                        return RedirectResponse(s["url"], status_code=302)

            # video by quality label
            for s in streams:
                if not s.get("url"):
                    continue
                label = str(s.get("qualityLabel", ""))
                if quality in label:
                    return RedirectResponse(s["url"], status_code=302)
        except:
            pass

    # ---- 2) yt-dlp 最終手段 ----
    try:
        fmt = "best"
        if quality == "360":
            fmt = "best[height<=360]/best"
        elif quality == "720":
            fmt = "best[height<=720]/best"
        elif quality == "audio":
            fmt = "bestaudio"

        cmd = [
            "yt-dlp",
            "-f", fmt,
            "-g",
            "--no-playlist",
            "--force-ipv4",
            "--no-check-certificates",
            "--user-agent", "Mozilla/5.0",
            f"https://www.youtube.com/watch?v={video_id}",
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=40,
        )

        urls = [u for u in p.stdout.splitlines() if u.startswith("http")]
        if urls:
            return RedirectResponse(urls[0], status_code=302)

        raise Exception(p.stderr)

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Download failed: {e}",
    )
