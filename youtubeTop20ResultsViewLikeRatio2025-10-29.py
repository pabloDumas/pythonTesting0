import os
import re
import json
import time
import math
import tempfile
import requests
import numpy as np
import pandas as pd
from urllib.parse import urlencode

# --------- Config ----------
API_KEY = os.getenv("YOUTUBE_API_KEY")  # <-- put your key in env
BASE = "https://www.googleapis.com/youtube/v3"
MAX_RESULTS = 20  # top N
ORDER = "relevance"  # or "viewCount", "date", etc.
# ---------------------------

def search_videos(query, max_results=MAX_RESULTS, order=ORDER):
    """Search YouTube for videos and return a list of video IDs (max 50 per call)."""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": order,
        "key": API_KEY,
    }
    resp = requests.get(f"{BASE}/search", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [item["id"]["videoId"] for item in data.get("items", []) if item["id"]["kind"] == "youtube#video"]

def get_video_stats(video_ids):
    """Fetch snippet + statistics for a list of video IDs."""
    if not video_ids:
        return []
    params = {
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }
    resp = requests.get(f"{BASE}/videos", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])

def safe_int(x):
    try:
        return int(x)
    except Exception:
        return np.nan

def keyword_to_safe_filename(s):
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "query"

def top20_table(query, out_dir=None):
    if not API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY environment variable.")

    video_ids = search_videos(query, max_results=MAX_RESULTS)
    items = get_video_stats(video_ids)

    rows = []
    for it in items:
        vid = it["id"]
        sn = it.get("snippet", {})
        st = it.get("statistics", {})

        title = sn.get("title", "")
        url = f"https://www.youtube.com/watch?v={vid}"
        views = safe_int(st.get("viewCount"))
        likes = safe_int(st.get("likeCount"))  # may be NaN if not provided
        if pd.isna(likes) or likes == 0:
            v2l = np.nan
        else:
            v2l = views / likes if not pd.isna(views) else np.nan

        rows.append({
            "title": title,
            "url": url,
            "views": views,
            "likes": likes,
            "view_to_like_ratio": v2l,
        })

    df = pd.DataFrame(rows)
    df["views"] = pd.to_numeric(df["views"], errors="coerce")
    df["likes"] = pd.to_numeric(df["likes"], errors="coerce")
    df["view_to_like_ratio"] = pd.to_numeric(df["view_to_like_ratio"], errors="coerce")

    # 🚩 Sort by highest view_to_like_ratio (NaN last)
    df = df.sort_values(
        by="view_to_like_ratio",
        ascending=False,
        na_position="last",
        kind="mergesort"
    ).reset_index(drop=True)

    # Save CSV (default: temp dir), filename includes keyword + timestamp
    if out_dir is None:
        out_dir = tempfile.gettempdir()
    os.makedirs(out_dir, exist_ok=True)
    fname = f"youtube_top20_{keyword_to_safe_filename(query)}_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    fpath = os.path.join(out_dir, fname)
    df.to_csv(fpath, index=False)

    return df, fpath

if __name__ == "__main__":
    QUERY = "transfer between brokers"  # <- replace with your keyword
    table, csv_path = top20_table(QUERY)
    print(table)
    print("\nSaved to:", csv_path)
