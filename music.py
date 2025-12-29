from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import requests

router = APIRouter(prefix="/api/sc", tags=["soundcloud"])

SC_CLIENT_ID = "Lz9s0yJ5EwXnX"  # 公開client_id（変更される可能性あり）
TIMEOUT = 6

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ===============================
# SoundCloud 検索
# ===============================
@router.get("/search")
def sc_search(q: str):
    url = "https://api-v2.soundcloud.com/search/tracks"

    params = {
        "q": q,
        "client_id": SC_CLIENT_ID,
        "limit": 20
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()

        results = []
        for t in data.get("collection", []):
            results.append({
                "id": t.get("id"),
                "title": t.get("title"),
                "username": t.get("user", {}).get("username"),
                "artwork_url": t.get("artwork_url"),
                "duration": t.get("duration"),
                "streamable": t.get("streamable")
            })

        return {
            "count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SoundCloud search failed: {e}")


# ===============================
# SoundCloud 再生URL取得
# ===============================
@router.get("/stream")
def sc_stream(track_id: str):
    track_url = f"https://api-v2.soundcloud.com/tracks/{track_id}"

    params = {
        "client_id": SC_CLIENT_ID
    }

    try:
        r = requests.get(track_url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        track = r.json()

        transcodings = track["media"]["transcodings"]

        for t in transcodings:
            if t["format"]["protocol"] == "progressive":
                r2 = requests.get(t["url"], params=params, timeout=TIMEOUT)
                r2.raise_for_status()
                return RedirectResponse(r2.json()["url"])

        raise HTTPException(status_code=404, detail="Playable stream not found")

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SoundCloud stream failed: {e}")
