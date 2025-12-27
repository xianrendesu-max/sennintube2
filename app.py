---

# app.py（完全・省略なし）

```python
import json
import urllib.parse
import requests

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UA = {"User-Agent": "Mozilla/5.0"}

INVIDIOUS = "https://pol1.iv.ggtyler.dev"
EDU_VIDEO_API = "https://siawaseok.duckdns.org/api/video2/"
EDU_STREAM_API = "https://siawaseok.duckdns.org/api/stream/"
YTDLP_API = "https://yudlp.vercel.app/stream/"
M3U8_API = "https://yudlp.vercel.app/m3u8/"

# =========================
# 検索
# =========================
@app.get("/api/search")
def api_search(q: str):
    url = f"{INVIDIOUS}/api/v1/search?q={urllib.parse.quote(q)}&hl=jp"
    r = requests.get(url, headers=UA, timeout=10)
    data = r.json()

    results = []
    for v in data:
        if v.get("type") == "video":
            results.append({
                "id": v.get("videoId"),
                "title": v.get("title"),
                "author": v.get("author")
            })

    return {
        "results": results,
        "used_instance": "invidious"
    }

# =========================
# 動画情報
# =========================
@app.get("/api/video/{videoid}")
def api_video(videoid: str):
    r = requests.get(EDU_VIDEO_API + videoid, headers=UA, timeout=10)
    t = r.json()

    return {
        "video": {
            "title": t.get("title", ""),
            "description_html": t.get("description", {}).get("formatted", "")
        },
        "related": t.get("related", [])
    }

# =========================
# コメント
# =========================
@app.get("/api/comments/{videoid}")
def api_comments(videoid: str):
    r = requests.get(
        f"{INVIDIOUS}/api/v1/comments/{videoid}",
        headers=UA,
        timeout=10
    )
    data = r.json()

    comments = []
    for c in data.get("comments", []):
        comments.append({
            "author": c.get("author"),
            "body": c.get("contentHtml")
        })

    return {"comments": comments}

# =========================
# ダウンロード
# =========================
@app.get("/api/download/{videoid}")
def api_download(videoid: str):
    r = requests.get(YTDLP_API + videoid, headers=UA, timeout=10)
    return r.json()

# =========================
# EDU embed
# =========================
@app.get("/api/edu/{videoid}", response_class=HTMLResponse)
def api_edu_embed(request: Request, videoid: str):
    r = requests.get(EDU_STREAM_API + videoid, headers=UA, timeout=10)
    url = r.json().get("url", "")

    return templates.TemplateResponse(
        "embed.html",
        {"request": request, "url": url}
    )

# =========================
# 高画質（M3U8）
# =========================
@app.get("/api/stream_high/{videoid}", response_class=HTMLResponse)
def api_stream_high(request: Request, videoid: str):
    r = requests.get(M3U8_API + videoid, headers=UA, timeout=10)
    formats = r.json().get("m3u8_formats", [])

    best = ""
    if formats:
        best = formats[-1].get("url", "")

    return templates.TemplateResponse(
        "embed_high.html",
        {"request": request, "url": best}
    )
