#!/usr/bin/env python3
"""Collect raw material for one morning feed: RSS items, new YouTube videos
(with transcript when available), market quotes. Writes work/raw.json.

Exit code 0 even when single sources fail (they are listed under health.failed).
Exit code 2 only when almost everything failed (likely network problem).
"""
import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) morning-feed/1.0"
PER_FEED = 12
TRANSCRIPT_CHARS = 12000


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child(el, name):
    for c in el:
        if local(c.tag) == name:
            return c
    return None


def text(el, name):
    c = child(el, name)
    return (c.text or "").strip() if c is not None and c.text else ""


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        d = None
    if d is None:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def clean(s, limit=400):
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def parse_feed(raw):
    root = ET.fromstring(raw)
    out = []
    for el in root.iter():
        kind = local(el.tag)
        if kind not in ("item", "entry"):
            continue
        title = clean(text(el, "title"), 300)
        link = text(el, "link")
        if not link:
            ln = child(el, "link")
            if ln is not None:
                link = ln.get("href", "")
        date = None
        for n in ("pubdate", "published", "updated", "date"):
            date = parse_date(text(el, n))
            if date:
                break
        desc = text(el, "description") or text(el, "summary") or text(el, "content")
        if title and link:
            out.append({"title": title, "url": link.strip(), "published": date, "summary": clean(desc)})
    return out


def fetch_feed(feed, since):
    items = parse_feed(get(feed["url"]))
    fresh = [i for i in items if i["published"] and i["published"] >= since]
    undated = [i for i in items if not i["published"]]
    fresh.sort(key=lambda i: i["published"], reverse=True)
    picked = (fresh or undated[:5])[:PER_FEED]
    for i in picked:
        i["published"] = i["published"].isoformat() if i["published"] else None
        i["source"] = feed["name"]
    return picked


def transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None, "youtube-transcript-api nicht installiert"
    try:
        api = YouTubeTranscriptApi()
        parts = api.fetch(video_id, languages=["de", "en"])
        txt = " ".join(p.text for p in parts)
        return re.sub(r"\s+", " ", txt)[:TRANSCRIPT_CHARS], None
    except Exception as e:  # blocked IP, no captions, ...
        return None, f"{type(e).__name__}"


def fetch_channel(ch, since):
    raw = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}")
    root = ET.fromstring(raw)
    vids = []
    for e in root.iter():
        if local(e.tag) != "entry":
            continue
        pub = parse_date(text(e, "published"))
        if not pub or pub < since:
            continue
        vid = text(e, "videoid")
        desc = ""
        for x in e.iter():
            if local(x.tag) == "description":
                desc = x.text or ""
        t, err = transcript(vid)
        vids.append({
            "channel": ch["name"], "topic": ch.get("topic"), "title": text(e, "title"),
            "url": f"https://www.youtube.com/watch?v={vid}", "published": pub.isoformat(),
            "description": clean(desc, 1500), "transcript": t, "transcript_error": err,
        })
    return vids


def fetch_quote(m):
    sym = urllib.request.quote(m["symbol"])
    data = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d"))
    res = data["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    price = res["meta"]["regularMarketPrice"]
    prev = closes[-2] if len(closes) >= 2 else res["meta"].get("chartPreviousClose")
    return {"name": m["name"], "price": price, "prev_close": prev,
            "change_pct": round((price / prev - 1) * 100, 2) if prev else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=None, help="Zeitfenster; Default 24h, montags 72h")
    ap.add_argument("--out", default=str(ROOT / "work" / "raw.json"))
    args = ap.parse_args()

    cfg = json.loads((ROOT / "sources.json").read_text())
    now = dt.datetime.now(dt.timezone.utc)
    hours = args.hours or (72 if now.astimezone().weekday() == 0 else 24)
    since = now - dt.timedelta(hours=hours)
    health = {"ok": [], "failed": []}

    def run(label, fn, *a):
        try:
            r = fn(*a)
            health["ok"].append(label)
            return r
        except Exception as e:
            health["failed"].append({"source": label, "error": f"{type(e).__name__}: {str(e)[:150]}"})
            return None

    sections = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        jobs = {}
        for s in cfg["sections"]:
            for f in s["feeds"]:
                jobs[pool.submit(run, f["name"], fetch_feed, f, since)] = s["id"]
        yt_jobs = [pool.submit(run, f"YouTube {c['name']}", fetch_channel, c, since) for c in cfg["youtube"]]
        mk_jobs = [pool.submit(run, f"Kurs {m['name']}", fetch_quote, m) for m in cfg["markets"]]
        for fut, sid in jobs.items():
            sections.setdefault(sid, []).extend(fut.result() or [])
        youtube = [v for j in yt_jobs for v in (j.result() or [])]
        markets = [r for r in (j.result() for j in mk_jobs) if r]

    out = {
        "generated_at": now.isoformat(), "window_hours": hours, "since": since.isoformat(),
        "section_titles": {s["id"]: s["title"] for s in cfg["sections"]},
        "sections": sections, "youtube": youtube, "markets": markets,
        "topic_fields": cfg["topic_fields"], "health": health,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    total = len(health["ok"]) + len(health["failed"])
    print(f"ok={len(health['ok'])} failed={len(health['failed'])} items={sum(map(len, sections.values()))} videos={len(youtube)} -> {args.out}")
    for f in health["failed"]:
        print(f"  FAILED {f['source']}: {f['error']}")
    if len(health["ok"]) < total * 0.3:
        sys.exit(2)


if __name__ == "__main__":
    main()
