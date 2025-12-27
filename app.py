from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import subprocess
import os

app = FastAPI()

# ===============================
# 静的ファイル
# ===============================
app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def root():
    return FileResponse("statics/index.html")


# ===============================
# Invidious インスタンス
# ===============================
VIDEO_INSTANCES = [
    "https://invidious.exma.de",
    "https://invidious.f5.si",
    "https://id.420129.xyz",
    "https://invid-api.poketube.fun",
    "https://cal1.iv.ggtyler.dev",
    "https://pol1.iv.ggtyler.dev"
]

SEARCH_INSTANCES = [
    "https://pol1.iv.ggtyler.dev",
    "https://youtube.mosesmang.com",
    "https://iteroni.com",
    "https://invidious.0011.lt",
    "https://iv.melmac.space"
]

COMMENT_INSTANCES = [
    "https://siawaseok-wakame-server2.glitch.me",
    "https://invidious.0011.lt",
    "https://invidious.nietzospannend.nl"
]

TIMEOUT = 6
HEADERS = {"User-Agent": "Mozilla/5.0"}


# ===============================
# 検索（完全総当たり）
# ===============================
@app.get("/api/search")
def api_search(q: str = Query(...)):
    instances = SEARCH_INSTANCES[:]
    random.shuffle(instances)

    for base in instances:
        for page in [1, 2]:
            try:
                r = requests.get(
                    f"{base}/api/v1/search",
                    params={
                        "q": q,
                        "type": "video",
                        "page": page
                    },
                    timeout=TIMEOUT,
                    headers=HEADERS
                )

                if r.status_code != 200:
                    continue

                data = r.json()
                if not isinstance(data, list) or not data:
                    continue

                results = []
                for v in data:
                    if v.get("videoId"):
                        results.append({
                            "videoId": v.get("videoId"),
                            "title": v.get("title"),
                            "author": v.get("author"),
                            "lengthSeconds": v.get("lengthSeconds"),
                            "viewCount": v.get("viewCount"),
                            "thumbnail": v.get("videoThumbnails", [{}])[-1].get("url")
                        })

                if results:
                    return {
                        "used_instance": base,
                        "results": results
                    }
            except:
                continue

    raise HTTPException(503, "Search unavailable (all instances failed)")


# ===============================
# 動画情報（完全総当たり）
# ===============================
@app.get("/api/video")
def api_video(video_id: str):
    instances = VIDEO_INSTANCES[:]
    random.shuffle(instances)

    for base in instances:
        try:
            r = requests.get(
                f"{base}/api/v1/videos/{video_id}",
                timeout=TIMEOUT,
                headers=HEADERS
            )

            if r.status_code != 200:
                continue

            data = r.json()
            if not data.get("title"):
                continue

            return {
                "used_instance": base,
                "video": {
                    "title": data.get("title"),
                    "author": data.get("author"),
                    "description": data.get("description"),
                    "viewCount": data.get("viewCount"),
                    "lengthSeconds": data.get("lengthSeconds"),
                    "recommended": data.get("recommendedVideos", [])
                }
            }
        except:
            continue

    raise HTTPException(503, "Video info unavailable")


# ===============================
# コメント（完全総当たり）
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str):
    instances = COMMENT_INSTANCES[:]
    random.shuffle(instances)

    for base in instances:
        for sort in ["top", "new"]:
            try:
                r = requests.get(
                    f"{base}/api/v1/comments/{video_id}",
                    params={"sort_by": sort},
                    timeout=TIMEOUT,
                    headers=HEADERS
                )

                if r.status_code != 200:
                    continue

                data = r.json()
                raw = data.get("comments", [])

                comments = []
                for c in raw:
                    if c.get("author") and c.get("content"):
                        comments.append({
                            "author": c.get("author"),
                            "content": c.get("content"),
                            "likes": c.get("likeCount", 0)
                        })

                if comments:
                    return {
                        "used_instance": base,
                        "comments": comments
                    }
            except:
                continue

    return {"comments": []}


# ===============================
# ダウンロード（完全総当たり）
# ===============================
@app.get("/api/download")
def api_download(video_id: str, quality: str = "360"):
    if quality == "audio":
        formats = ["bestaudio", "ba"]
    elif quality == "720":
        formats = [
            "bestvideo[height<=720]+bestaudio/best",
            "best[height<=720]",
            "best"
        ]
    else:
        formats = [
            "bestvideo[height<=360]+bestaudio/best",
            "best[height<=360]",
            "best"
        ]

    last_error = None

    for fmt in formats:
        try:
            cmd = [
                "yt-dlp",
                "-f", fmt,
                "-g",
                "--no-playlist",
                "--force-ipv4",
                "--no-check-certificates",
                f"https://www.youtube.com/watch?v={video_id}"
            ]

            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45
            )

            urls = [u for u in p.stdout.splitlines() if u.startswith("http")]

            if urls:
                return RedirectResponse(urls[0], status_code=302)

            last_error = p.stderr
        except Exception as e:
            last_error = str(e)

    raise HTTPException(500, f"Download failed: {last_error}")
