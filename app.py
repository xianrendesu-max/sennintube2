from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import requests
import random
import os

app = FastAPI()

# ===============================
# Invidious インスタンス（用途別）
# ===============================
INSTANCES = {
    "video": [
        "https://invidious.exma.de",
        "https://invidious.f5.si",
        "https://siawaseok-wakame-server2.glitch.me",
        "https://lekker.gay",
        "https://id.420129.xyz",
        "https://invid-api.poketube.fun",
        "https://eu-proxy.poketube.fun",
        "https://cal1.iv.ggtyler.dev",
        "https://pol1.iv.ggtyler.dev"
    ],
    "search": [
        "https://pol1.iv.ggtyler.dev",
        "https://youtube.mosesmang.com",
        "https://iteroni.com",
        "https://invidious.0011.lt",
        "https://iv.melmac.space",
        "https://rust.oskamp.nl"
    ],
    "channel": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://id.420129.xyz",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl"
    ],
    "playlist": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl",
        "https://youtube.mosesmang.com",
        "https://iv.melmac.space",
        "https://lekker.gay"
    ],
    "comments": [
        "https://siawaseok-wakame-server2.glitch.me",
        "https://invidious.0011.lt",
        "https://invidious.nietzospannend.nl"
    ]
}

# ===============================
# 共通リクエスト（フェイルオーバー）
# ===============================
def fetch_with_fallback(instances, path, params=None):
    random.shuffle(instances)

    for base in instances:
        try:
            r = requests.get(
                f"{base}{path}",
                params=params,
                timeout=10
            )
            r.raise_for_status()
            return r.json(), base
        except Exception:
            continue

    raise HTTPException(
        status_code=502,
        detail="All Invidious instances failed"
    )

# ===============================
# API : 検索
# ===============================
@app.get("/api/search")
def api_search(q: str):
    data, used = fetch_with_fallback(
        INSTANCES["search"],
        "/api/v1/search",
        {"q": q, "type": "video"}
    )
    return {
        "results": data,
        "used_instance": used
    }

# ===============================
# API : トレンド
# ===============================
@app.get("/api/trending")
def api_trending(region: str = "JP"):
    data, _ = fetch_with_fallback(
        INSTANCES["search"],
        "/api/v1/trending",
        {"region": region}
    )
    return data

# ===============================
# API : 動画情報 + 関連動画
# ===============================
@app.get("/api/video")
def api_video(video_id: str):
    data, used = fetch_with_fallback(
        INSTANCES["video"],
        f"/api/v1/videos/{video_id}"
    )

    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "author": data.get("author"),
        "viewCount": data.get("viewCount"),
        "recommended": data.get("recommendedVideos", []),
        "used_instance": used
    }

# ===============================
# API : コメント
# ===============================
@app.get("/api/comments")
def api_comments(video_id: str):
    data, used = fetch_with_fallback(
        INSTANCES["comments"],
        f"/api/v1/comments/{video_id}"
    )
    data["used_instance"] = used
    return data

# ===============================
# API : チャンネル情報
# ===============================
@app.get("/api/channel")
def api_channel(channel_id: str):
    data, used = fetch_with_fallback(
        INSTANCES["channel"],
        f"/api/v1/channels/{channel_id}"
    )
    data["used_instance"] = used
    return data

# ===============================
# API : プレイリスト
# ===============================
@app.get("/api/playlist")
def api_playlist(list_id: str):
    data, used = fetch_with_fallback(
        INSTANCES["playlist"],
        f"/api/v1/playlists/{list_id}"
    )
    data["used_instance"] = used
    return data

# ===============================
# API : ダウンロード（360p / m3u8）
# ===============================
@app.get("/api/download")
def api_download(video_id: str):
    data, _ = fetch_with_fallback(
        INSTANCES["video"],
        f"/api/v1/videos/{video_id}"
    )

    formats = []

    for f in data.get("adaptiveFormats", []):
        url = f.get("url")
        if not url:
            continue

        if f.get("itag") == "18":
            formats.append({
                "quality": "360p",
                "type": "mp4",
                "url": url
            })

        if "m3u8" in f.get("type", ""):
            formats.append({
                "quality": f.get("qualityLabel", "auto"),
                "type": "m3u8",
                "url": url
            })

    if not formats:
        raise HTTPException(404, "No downloadable formats")

    return {"formats": formats}

# ===============================
# 静的ファイル
# / → index.html（307なし）
# ===============================
if not os.path.isdir("statics"):
    raise RuntimeError("Directory 'statics' does not exist")

app.mount(
    "/",
    StaticFiles(directory="statics", html=True),
    name="static"
    )
