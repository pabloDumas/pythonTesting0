#python "C:\Users\pablo\OneDrive\Documents\2026-10-21T14-24-00.youtubeSearch.videoComments.tkinterGUI.py"
"""
2026-10-21T15-04-05. Will not work in GitHub Code Spaces unless you install a GUI. 
YouTube keyword search -> top X videos -> metadata + all comments -> one text file.

- Searches YouTube the way a person would (default "Relevance" ranking, videos only).
- For the first X results, writes each video's details at the top of its section and
  all comments (and replies, optional) underneath.
- Separates each video's section with blank lines plus a divider line.
- Shows the full path of the text file when it's done.

Setup (one time):
    pip install requests
    Get a free YouTube Data API v3 key: https://console.cloud.google.com/
      -> create a project -> enable "YouTube Data API v3" -> Credentials -> API key
    Optional: set environment variable YOUTUBE_API_KEY so the key fills in automatically.

Daily limit: 10,000 units by default. Each search page costs 100 units, and each page
of comments (up to 100 comments) costs 1 unit, so normal use fits easily.
"""
import os
import re
import sys
import time
import queue
import threading
import datetime as dt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

try:
    import requests
except ImportError:
    print("Missing package 'requests'. Run:  pip install requests")
    sys.exit(1)

API = "https://www.googleapis.com/youtube/v3"
BLANK_LINES_BETWEEN_VIDEOS = 12          # blank lines between each video's section
DIVIDER = "#" * 110


# ----------------------------------------------------------------------------- API helpers
class StopAll(Exception):
    """Stops the whole run (bad key or daily limit reached)."""


class SkipVideo(Exception):
    """Skips comments for one video (comments turned off, video removed, etc.)."""


def api_get(endpoint, params, key):
    params = {k: v for k, v in dict(params, key=key).items() if v is not None}
    for attempt in range(1, 4):
        try:
            r = requests.get(f"{API}/{endpoint}", params=params, timeout=30)
        except requests.RequestException as e:
            if attempt == 3:
                raise SkipVideo(f"Network error: {e}")
            time.sleep(2 * attempt)
            continue
        if r.status_code == 200:
            return r.json()
        try:
            err = r.json().get("error", {})
        except ValueError:
            err = {}
        reason = (err.get("errors") or [{}])[0].get("reason", "")
        msg = err.get("message", r.text[:200])
        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            raise StopAll("Daily YouTube API limit reached. Try again tomorrow (resets midnight Pacific).")
        if reason in ("keyInvalid", "forbidden", "accessNotConfigured") or "API key" in msg:
            raise StopAll(f"API key problem: {msg}")
        if reason == "commentsDisabled":
            raise SkipVideo("Comments are turned off for this video.")
        if r.status_code in (500, 503) and attempt < 3:
            time.sleep(2 * attempt)
            continue
        raise SkipVideo(f"YouTube returned {r.status_code} ({reason or 'error'}): {msg}")
    raise SkipVideo("Request failed after 3 tries.")


def search_videos(query, n, key):
    ids, token = [], None
    while len(ids) < n:
        data = api_get("search", {
            "part": "id", "q": query, "type": "video", "order": "relevance",
            "maxResults": min(50, n - len(ids)), "pageToken": token,
        }, key)
        for it in data.get("items", []):
            vid = it.get("id", {}).get("videoId")
            if vid and vid not in ids:
                ids.append(vid)
        token = data.get("nextPageToken")
        if not token:
            break
    return ids[:n]


def get_video_details(ids, key):
    details = {}
    for i in range(0, len(ids), 50):
        data = api_get("videos", {
            "part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50]),
        }, key)
        for it in data.get("items", []):
            details[it["id"]] = it
    return details


def get_all_replies(parent_id, key):
    replies, token = [], None
    while True:
        data = api_get("comments", {
            "part": "snippet", "parentId": parent_id, "maxResults": 100,
            "textFormat": "plainText", "pageToken": token,
        }, key)
        replies += [c["snippet"] for c in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            return replies


def get_comments(video_id, key, max_comments, include_replies, order, progress):
    threads, token, page = [], None, 0
    while True:
        page += 1
        data = api_get("commentThreads", {
            "part": "snippet,replies" if include_replies else "snippet",
            "videoId": video_id, "maxResults": 100, "order": order,
            "textFormat": "plainText", "pageToken": token,
        }, key)
        for th in data.get("items", []):
            top = th["snippet"]["topLevelComment"]["snippet"]
            n_replies = th["snippet"].get("totalReplyCount", 0)
            replies = []
            if include_replies and n_replies:
                inline = [c["snippet"] for c in th.get("replies", {}).get("comments", [])]
                replies = inline if len(inline) >= n_replies else get_all_replies(th["id"], key)
                replies.sort(key=lambda s: s.get("publishedAt", ""))
            threads.append((top, n_replies, replies))
            if max_comments and len(threads) >= max_comments:
                return threads
        progress(f"      comments page {page}: {len(threads):,} top-level comments so far")
        token = data.get("nextPageToken")
        if not token:
            return threads


# ----------------------------------------------------------------------------- formatting
def nice_duration(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return iso or "n/a"
    d, h, mi, s = (int(x or 0) for x in m.groups())
    h += d * 24
    return f"{h}:{mi:02d}:{s:02d}" if h else f"{mi}:{s:02d}"


def num(v):
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "hidden/n/a"


def indent(text, pad):
    return ("\n" + pad).join((text or "").splitlines() or [""])


def video_header(i, total, vid, item, query):
    sn = item.get("snippet", {}) if item else {}
    st = item.get("statistics", {}) if item else {}
    cd = item.get("contentDetails", {}) if item else {}
    return "\n".join([
        DIVIDER,
        f"VIDEO {i} of {total}   |   search: \"{query}\"   |   search rank: {i}",
        DIVIDER,
        f"Title:          {sn.get('title', 'n/a')}",
        f"URL:            https://www.youtube.com/watch?v={vid}",
        f"Video ID:       {vid}",
        f"Channel:        {sn.get('channelTitle', 'n/a')}  (https://www.youtube.com/channel/{sn.get('channelId', '')})",
        f"Published:      {sn.get('publishedAt', 'n/a')}",
        f"Duration:       {nice_duration(cd.get('duration'))}",
        f"Views:          {num(st.get('viewCount'))}",
        f"Likes:          {num(st.get('likeCount'))}",
        f"Comment count:  {num(st.get('commentCount'))}",
        f"Tags:           {', '.join(sn.get('tags', [])) or 'none'}",
        "Description:",
        "    " + indent(sn.get("description", ""), "    "),
        "-" * 110,
    ])


def comments_block(threads, note=None):
    if note:
        return f"COMMENTS: {note}\n"
    out = [f"COMMENTS ({len(threads):,} top-level shown):", ""]
    for n, (c, n_rep, replies) in enumerate(threads, 1):
        out.append(f"[{n}] {c.get('authorDisplayName', '?')} | {c.get('publishedAt', '')} "
                   f"| likes: {c.get('likeCount', 0)} | replies: {n_rep}")
        out.append("    " + indent(c.get("textDisplay", ""), "    "))
        for r in replies:
            out.append(f"        -> {r.get('authorDisplayName', '?')} | {r.get('publishedAt', '')} "
                       f"| likes: {r.get('likeCount', 0)}")
            out.append("           " + indent(r.get("textDisplay", ""), "           "))
        out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------------- worker
def run_job(cfg, log, set_progress, done):
    t0 = time.perf_counter()
    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    def L(msg):
        e = time.perf_counter() - t0
        log(f"[{int(e // 60):02d}:{e % 60:04.1f}] {msg}")

    slug = re.sub(r"[^A-Za-z0-9]+", "_", cfg["query"]).strip("_")[:60] or "search"
    path = os.path.join(cfg["folder"], f"{stamp}.youtubeComments.{slug}.top{cfg['n']}.txt")
    written = 0
    try:
        L(f"Step 1 of 4: searching YouTube for \"{cfg['query']}\" (top {cfg['n']})...")
        ids = search_videos(cfg["query"], cfg["n"], cfg["key"])
        L(f"Step 1 of 4: found {len(ids)} videos.")
        if not ids:
            done(None, "No videos found for that search.")
            return

        L(f"Step 2 of 4: getting details for {len(ids)} videos...")
        details = get_video_details(ids, cfg["key"])
        L("Step 2 of 4: details received.")

        L(f"Step 3 of 4: getting comments and writing file -> {path}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"YouTube search: \"{cfg['query']}\"\nRun at: {stamp}\n"
                    f"Videos requested: {cfg['n']} | found: {len(ids)} | "
                    f"max comments/video: {cfg['max_c'] or 'all'} | replies: {cfg['replies']} | "
                    f"comment order: {cfg['order']}\n")
            for i, vid in enumerate(ids, 1):
                item = details.get(vid)
                title = (item or {}).get("snippet", {}).get("title", vid)
                L(f"Step 3 of 4: video {i} of {len(ids)}: {title[:70]}")
                note, threads = None, []
                try:
                    threads = get_comments(vid, cfg["key"], cfg["max_c"], cfg["replies"],
                                           cfg["order"], L)
                    n_rep = sum(len(r) for _, _, r in threads)
                    L(f"      done: {len(threads):,} comments + {n_rep:,} replies")
                except SkipVideo as e:
                    note = str(e)
                    L(f"      skipped comments: {note}")
                f.write("\n" * BLANK_LINES_BETWEEN_VIDEOS)
                f.write(video_header(i, len(ids), vid, item, cfg["query"]) + "\n")
                f.write(comments_block(threads, note))
                f.flush()
                written += 1
                set_progress(i, len(ids))

        e = time.perf_counter() - t0
        L(f"Step 4 of 4: finished. {written} videos written. Total time {int(e // 60)}m {e % 60:.1f}s")
        done(path, None)
    except StopAll as e:
        L(f"STOPPED: {e}")
        done(path if written else None, f"{e}\n\n{written} videos were saved before stopping.")
    except Exception as e:
        L(f"ERROR: {e!r}")
        done(path if written else None, f"Unexpected error: {e!r}")


# ----------------------------------------------------------------------------- GUI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Search -> Video Comments to Text File")
        self.geometry("900x640")
        self.minsize(700, 500)
        self.q = queue.Queue()
        self._build()
        self.after(100, self._poll)

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        self.key = tk.StringVar(value=os.environ.get("YOUTUBE_API_KEY", ""))
        self.query = tk.StringVar(value="claude vs chatgpt")
        self.n = tk.IntVar(value=10)
        self.max_c = tk.IntVar(value=0)
        self.replies = tk.BooleanVar(value=True)
        self.order = tk.StringVar(value="relevance")
        self.folder = tk.StringVar(value=os.path.dirname(os.path.abspath(__file__)))
        self.result = tk.StringVar()
        self.show_key = tk.BooleanVar(value=False)

        r = 0
        ttk.Label(frm, text="YouTube API key:").grid(row=r, column=0, sticky="w")
        self.key_entry = ttk.Entry(frm, textvariable=self.key, show="*")
        self.key_entry.grid(row=r, column=1, sticky="ew", padx=5)
        ttk.Checkbutton(frm, text="Show", variable=self.show_key,
                        command=lambda: self.key_entry.config(show="" if self.show_key.get() else "*")
                        ).grid(row=r, column=2, sticky="w")
        r += 1
        ttk.Label(frm, text="Search keywords:").grid(row=r, column=0, sticky="w", pady=4)
        qe = ttk.Entry(frm, textvariable=self.query)
        qe.grid(row=r, column=1, columnspan=2, sticky="ew", padx=5)
        qe.bind("<Return>", lambda e: self.start())
        r += 1
        opts = ttk.Frame(frm)
        opts.grid(row=r, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Label(opts, text="Number of videos (X):").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=500, textvariable=self.n, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(opts, text="Max comments per video (0 = all):").pack(side="left")
        ttk.Spinbox(opts, from_=0, to=100000, increment=100, textvariable=self.max_c, width=8
                    ).pack(side="left", padx=(4, 16))
        ttk.Checkbutton(opts, text="Include replies", variable=self.replies).pack(side="left", padx=(0, 16))
        ttk.Label(opts, text="Comment order:").pack(side="left")
        ttk.Combobox(opts, textvariable=self.order, values=["relevance", "time"], width=10,
                     state="readonly").pack(side="left", padx=4)
        r += 1
        ttk.Label(frm, text="Save folder:").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.folder).grid(row=r, column=1, sticky="ew", padx=5)
        ttk.Button(frm, text="Browse...", command=self._browse).grid(row=r, column=2, sticky="w")
        r += 1
        self.run_btn = ttk.Button(frm, text="Search and get comments", command=self.start)
        self.run_btn.grid(row=r, column=0, sticky="w", pady=8)
        self.pbar = ttk.Progressbar(frm, mode="determinate")
        self.pbar.grid(row=r, column=1, columnspan=2, sticky="ew", padx=5)
        r += 1
        self.logbox = ScrolledText(frm, height=18, wrap="word", font=("Consolas", 9))
        self.logbox.grid(row=r, column=0, columnspan=3, sticky="nsew")
        frm.rowconfigure(r, weight=1)
        r += 1
        ttk.Label(frm, text="Output file:").grid(row=r, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frm, textvariable=self.result, state="readonly").grid(
            row=r, column=1, sticky="ew", padx=5, pady=(8, 0))
        btns = ttk.Frame(frm)
        btns.grid(row=r, column=2, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="Copy", command=self._copy).pack(side="left")
        ttk.Button(btns, text="Open", command=lambda: self._open(self.result.get())).pack(side="left")
        ttk.Button(btns, text="Folder",
                   command=lambda: self._open(os.path.dirname(self.result.get()))).pack(side="left")

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get())
        if d:
            self.folder.set(d)

    def _copy(self):
        if self.result.get():
            self.clipboard_clear()
            self.clipboard_append(self.result.get())

    def _open(self, p):
        if p and os.path.exists(p):
            if sys.platform.startswith("win"):
                os.startfile(p)
            else:
                import subprocess
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", p])

    def start(self):
        try:
            n, max_c = int(self.n.get()), int(self.max_c.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Check inputs", "Number of videos and max comments must be whole numbers.")
            return
        cfg = {"key": self.key.get().strip(), "query": self.query.get().strip(),
               "n": max(1, min(n, 500)), "max_c": max(0, max_c), "replies": self.replies.get(),
               "order": self.order.get(), "folder": self.folder.get().strip()}
        if not cfg["key"]:
            messagebox.showerror("Missing API key", "Enter your YouTube Data API v3 key.")
            return
        if not cfg["query"]:
            messagebox.showerror("Missing keywords", "Enter search keywords.")
            return
        if not os.path.isdir(cfg["folder"]):
            messagebox.showerror("Bad folder", "The save folder does not exist.")
            return
        self.run_btn.config(state="disabled")
        self.result.set("")
        self.pbar.config(value=0, maximum=cfg["n"])
        self.logbox.delete("1.0", "end")
        threading.Thread(target=run_job, daemon=True, args=(
            cfg,
            lambda m: self.q.put(("log", m)),
            lambda i, t: self.q.put(("prog", (i, t))),
            lambda p, err: self.q.put(("done", (p, err))),
        )).start()

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    print(val)
                    self.logbox.insert("end", val + "\n")
                    self.logbox.see("end")
                elif kind == "prog":
                    self.pbar.config(value=val[0], maximum=val[1])
                elif kind == "done":
                    path, err = val
                    self.run_btn.config(state="normal")
                    if path:
                        full = os.path.abspath(path)
                        self.result.set(full)
                        print(f"OUTPUT FILE: {full}")
                        self.logbox.insert("end", f"\nOUTPUT FILE: {full}\n")
                        self.logbox.see("end")
                    if err:
                        messagebox.showwarning("Finished with a problem", err)
        except queue.Empty:
            pass
        self.after(100, self._poll)


if __name__ == "__main__":
    App().mainloop()
