#!/usr/bin/env python3
import os
import re
import time
import argparse
from urllib.parse import urlparse, parse_qs

import requests

# --------- Config ----------
API_KEY = os.getenv("YOUTUBE_API_KEY")  # <-- env var with your key
BASE = "https://www.googleapis.com/youtube/v3"
MAX_RESULTS = 100          # max per API page
ORDER = "time"             # "time" or "relevance"
TEXT_FORMAT = "plainText"  # YouTube API valid: "plainText" or "html"
# ---------------------------


def extract_video_id(url_or_id: str) -> str:
    """
    Extract a YouTube video ID from a full URL or return the ID if already given.
    Handles typical watch, youtu.be, shorts, embed URLs.
    """
    url_or_id = url_or_id.strip()

    # If it looks like a bare video ID
    if "http" not in url_or_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id

    parsed = urlparse(url_or_id)

    # Short link: https://youtu.be/VIDEOID
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/")

    # Standard YouTube domains
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        qs = parse_qs(parsed.query)

        # Standard watch URL: https://www.youtube.com/watch?v=VIDEOID
        if "v" in qs and qs["v"]:
            return qs["v"][0]

        # Shorts: https://www.youtube.com/shorts/VIDEOID
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/")[1].split("/")[0]

        # Embed: https://www.youtube.com/embed/VIDEOID
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/")[1].split("/")[0]

    raise ValueError(
        f"Could not extract video ID from input: {url_or_id!r}. "
        "Provide a full YouTube URL or an 11-character video ID."
    )


def safe_for_filename(s: str) -> str:
    """
    Convert an arbitrary string (URL or ID) to a filesystem-safe chunk.
    """
    s = s.strip()
    if not s:
        return "video"
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "video"


def fetch_replies(parent_id: str, text_format: str = TEXT_FORMAT):
    """
    Fetch all replies to a top-level comment using comments.list.
    Returns a list of comment dicts (replies).
    """
    all_replies = []
    page_token = None

    while True:
        params = {
            "part": "snippet",
            "parentId": parent_id,
            "maxResults": MAX_RESULTS,
            "textFormat": text_format,
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(f"{BASE}/comments", params=params, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            # Try to print API error message for debugging
            try:
                err = resp.json()
                print("Error fetching replies:", err)
            except Exception:
                print("Error fetching replies, status:", resp.status_code, resp.text[:500])
            raise

        data = resp.json()

        for item in data.get("items", []):
            sn = item["snippet"]
            all_replies.append({
                "comment_id": item["id"],
                "parent_id": parent_id,
                "is_reply": True,
                "author": sn.get("authorDisplayName", ""),
                "published_at": sn.get("publishedAt", ""),
                "updated_at": sn.get("updatedAt", ""),
                "like_count": sn.get("likeCount", 0),
                "text": (sn.get("textOriginal", "") or "")
                        .replace("\r\n", "\n").replace("\r", "\n"),
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_replies


def fetch_all_comments(video_id: str, text_format: str = TEXT_FORMAT):
    """
    Fetch all top-level comments and all their replies for the given video_id.
    Returns a list of comment dicts.
    """
    all_comments = []
    page_token = None

    while True:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": MAX_RESULTS,
            "textFormat": text_format,
            "order": ORDER,
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(f"{BASE}/commentThreads", params=params, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            # Print API error JSON for debugging
            try:
                err = resp.json()
                print("Error fetching comment threads:", err)
            except Exception:
                print("Error fetching comment threads, status:",
                      resp.status_code, resp.text[:500])
            raise

        data = resp.json()

        items = data.get("items", [])
        if not items and not data.get("nextPageToken"):
            # No comments, or comments disabled, or video not found
            break

        for item in items:
            snippet = item["snippet"]
            top = snippet["topLevelComment"]
            top_sn = top["snippet"]
            top_id = top["id"]

            # Top-level comment
            all_comments.append({
                "comment_id": top_id,
                "parent_id": None,
                "is_reply": False,
                "author": top_sn.get("authorDisplayName", ""),
                "published_at": top_sn.get("publishedAt", ""),
                "updated_at": top_sn.get("updatedAt", ""),
                "like_count": top_sn.get("likeCount", 0),
                "text": (top_sn.get("textOriginal", "") or "")
                        .replace("\r\n", "\n").replace("\r", "\n"),
            })

            # Fetch all replies if any
            total_replies = snippet.get("totalReplyCount", 0)
            if total_replies:
                replies = fetch_replies(top_id, text_format=text_format)
                all_comments.extend(replies)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_comments


def save_comments_to_file(comments, video_id: str, label: str, out_dir: str | None = None) -> str:
    """
    Save all comments into a single UTF-8 text file.
    out_dir:
        - None  -> current working directory (os.getcwd()).
        - else  -> that directory (created if missing).
    File name format:
        YouTube_comments_for_video_<safe(label)>_<YYYYMMDD>.txt
    """
    if out_dir is None:
        out_dir = os.getcwd()

    os.makedirs(out_dir, exist_ok=True)

    today = time.strftime("%Y%m%d")
    safe_label = safe_for_filename(label)
    fname = f"YouTube_comments_for_video_{safe_label}_{today}.txt"
    fpath = os.path.join(out_dir, fname)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"Video ID: {video_id}\n")
        f.write(f"Original input: {label}\n")
        f.write(f"Total comments (including replies): {len(comments)}\n")
        f.write("=" * 80 + "\n\n")

        for idx, c in enumerate(comments, start=1):
            kind = "reply" if c["is_reply"] else "top"
            f.write(f"#{idx} [{kind}]\n")
            f.write(f"comment_id: {c['comment_id']}\n")
            if c["parent_id"]:
                f.write(f"parent_id: {c['parent_id']}\n")
            f.write(f"author: {c['author']}\n")
            f.write(f"published_at: {c['published_at']}\n")
            f.write(f"likes: {c['like_count']}\n\n")
            f.write(c["text"])
            f.write("\n" + "-" * 80 + "\n\n")

    return fpath


def parse_args():
    parser = argparse.ArgumentParser(
        description="Dump all YouTube comments for a video into a text file."
    )
    parser.add_argument(
        "video",
        help="YouTube video URL or 11-character video ID"
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory to save the .txt file (default: current working directory)",
    )
    return parser.parse_args()


def main():
    if not API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY environment variable.")

    args = parse_args()
    video_input = args.video
    video_id = extract_video_id(video_input)

    print(f"Fetching comments for video: {video_id} ...")
    comments = fetch_all_comments(video_id)
    print(f"Fetched {len(comments)} comments (including replies).")

    out_path = save_comments_to_file(
        comments=comments,
        video_id=video_id,
        label=video_input,
        out_dir=args.out_dir,
    )
    print("Saved to:", out_path)


if __name__ == "__main__":
    main()
