from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import os
import subprocess
import uuid

app = FastAPI()

# ===============================
# Static
# ===============================
if os.path.isdir("statics"):
    app.mount("/static", StaticFiles(directory="statics"), name="static")

    if os.path.isdir("statics/music"):
        app.mount("/music", StaticFiles(directory="statics/music", html=True), name="music")
else:
    print("⚠ statics directory not found")

@app.get("/")
def root():
    if os.path.isfile("statics/index.html"):
        return FileResponse("statics/index.html")
    return {"status": "index.html not found"}

# ===============================
# API BASE
# ===============================
VIDEO_APIS = [
    "https://iv.melmac.space",
    "https://pol1.iv.ggtyler.dev",
    "https://cal1.iv.ggtyler.dev",
    "https://invidious.0011.lt",
    "https://yt.omada.cafe",
]

COMMENTS_APIS = [
    "https://invidious.lunivers.trade",
    "https://invidious.ducks.party",
    "https://super8.absturztau.be",
    "https://invidious.nikkosphere.com",
    "https://yt.omada.cafe",
]

TIMEOUT = 6
HEADERS = {"User-Agent": "Mozilla/5.0"}

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

def pick_video_audio(formats, quality="best"):
    video_url = None
    audio_url = None

    # 映像（video only）
    for f in formats:
        if f.get("type", "").startswith("video") and f.get("url"):
            label = f.get("qualityLabel") or ""
            if quality == "best" or quality in label:
                video_url = f["url"]
                break

    # 音声（日本語 or 非英語優先）
    for f in formats:
        if f.get("type", "").startswith("audio") and f.get("url"):
            lang = (f.get("language") or "").lower()
            if "en" in lang:
                continue
            audio_url = f["url"]
            break

    return video_url, audio_url

def mux_video_audio_ios(video_url, audio_url):
    out = f"/tmp/{uuid.uuid4()}.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_url,
        "-i", audio_url,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        out
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out

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
                    {"author": c.get("author"), "content": c.get("content")}
                    for c in data.get("comments", [])
                ]
            }
    return {"comments": []}

# ===============================
# Stream（iOS向け：合成）
# ===============================
@app.get("/api/stream")
def api_stream(video_id: str, quality: str = "best"):
    for base in VIDEO_APIS:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue

        video_url, audio_url = pick_video_audio(
            data.get("adaptiveFormats", []),
            quality
        )

        if not video_url or not audio_url:
            continue

        output = mux_video_audio_ios(video_url, audio_url)

        return FileResponse(
            output,
            media_type="video/mp4",
            filename=f"{video_id}.mp4"
        )

    raise HTTPException(status_code=503, detail="Stream unavailable")

# ===============================
# Stream URL（Web向け：JSON）
# ===============================
@app.get("/api/streamurl")
def api_streamurl(video_id: str, quality: str = "best"):
    random.shuffle(VIDEO_APIS)

    for base in VIDEO_APIS:
        data = try_json(f"{base}/api/v1/videos/{video_id}")
        if not data:
            continue

        video_url, audio_url = pick_video_audio(
            data.get("adaptiveFormats", []),
            quality
        )

        if video_url and audio_url:
            return {
                "video": video_url,
                "audio": audio_url,
                "source": base
            }

    raise HTTPException(status_code=503, detail="Stream URL unavailable")
