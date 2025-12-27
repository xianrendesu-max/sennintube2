from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import random
import time

app = FastAPI()

# =========================
# Invidious instances
# =========================
INSTANCES = [
    "https://pol1.iv.ggtyler.dev",
    "https://cal1.iv.ggtyler.dev",
    "https://iv.melmac.space",
    "https://invidious.0011.lt",
    "https://id.420129.xyz"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Encoding": "identity"
}

# =========================
# Utility
# =========================
def try_instances(path, params=None):
    last_error = None
    for base in INSTANCES:
        try:
            r = requests.get(
                base + path,
                params=params,
                headers=HEADERS,
                timeout=12
            )
            if r.status_code == 200:
                return r.json(), base
        except Exception as e:
            last_error = e
            continue
    raise HTTPException(503, f"Invidious unavailable: {last_error}")

# =========================
# Static
# =========================
app.mount("/static", StaticFiles(directory="statics"), name="static")

@app.get("/")
def root():
    return FileResponse("statics/index.html")

# =========================
# Search
# =========================
@app.get("/api/search")
def search(q: str):
    data, used = try_instances(
        "/api/v1/search",
        {"q": q, "type": "video"}
    )
    return {"results": data, "used": used}

# =========================
# Video / Related / Channel
# =========================
@app.get("/api/video/{vid}")
def video(vid: str):
    data, used = try_instances(f"/api/v1/videos/{vid}")
    return {
        "video": data,
        "related": data.get("recommendedVideos", []),
        "used": used
    }

# =========================
# Channel info
# =========================
@app.get("/api/channel/{cid}")
def channel(cid: str):
    data, used = try_instances(f"/api/v1/channels/{cid}")
    return data

# =========================
# Comments
# =========================
@app.get("/api/comments/{vid}")
def comments(vid: str):
    data, used = try_instances(f"/api/v1/comments/{vid}")
    return data

# =========================
# Download (超安定)
# =========================
@app.get("/api/download/{vid}")
def download(vid: str, itag: str):
    info, _ = try_instances(f"/api/v1/videos/{vid}")

    target = None
    for f in info.get("formatStreams", []):
        if f.get("itag") == itag and f.get("url"):
            target = f
            break

    if not target:
        raise HTTPException(404, "format not found")

    def stream():
        with requests.get(
            target["url"],
            headers=HEADERS,
            stream=True,
            timeout=15
        ) as r:
            r.raise_for_status()
            for chunk in r.iter_content(1024 * 256):
                if chunk:
                    yield chunk
                    time.sleep(0.001)

    return StreamingResponse(
        stream(),
        media_type=target.get("mimeType", "video/mp4"),
        headers={
            "Content-Disposition": f'attachment; filename="{vid}.mp4"',
            "Accept-Ranges": "bytes"
        }
    )
