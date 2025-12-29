from fastapi import FastAPI, HTTPException, Query
import requests
import os

app = FastAPI()

# ===============================
# SoundCloud 設定
# ===============================
SOUNDCLOUD_CLIENT_ID = os.getenv(
    "SOUNDCLOUD_CLIENT_ID",
    "YOUR_CLIENT_ID_HERE"
)

SEARCH_URL = "https://api-v2.soundcloud.com/search/tracks"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ===============================
# 検索API
# ===============================
@app.get("/music/search")
def search_music(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50)
):
    params = {
        "q": q,
        "limit": limit,
        "client_id": SOUNDCLOUD_CLIENT_ID
    }

    try:
        res = requests.get(
            SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=10
        )
    except Exception:
        raise HTTPException(status_code=502, detail="SoundCloud接続失敗")

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="SoundCloud API error")

    data = res.json()

    tracks = []
    for t in data.get("collection", []):
        tracks.append({
            "id": t.get("id"),
            "title": t.get("title"),
            "username": t.get("user", {}).get("username"),
            "artwork_url": t.get("artwork_url")
        })

    return {
        "query": q,
        "count": len(tracks),
        "tracks": tracks
    }
