#!/usr/bin/env python3
"""Render content/<date>.json (written by the routine) into docs/d/<date>.html,
rebuild docs/index.html (latest + archive) and write work/telegram.txt.

Markets and source health come from work/raw.json, not from the LLM.
"""
import datetime as dt
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
BASE_URL = "https://damwier.github.io/morning-feed"
WD = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MON = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
       "September", "Oktober", "November", "Dezember"]

CSS = """
:root{--bg:#faf8f5;--fg:#1d1b19;--muted:#6b655e;--line:#e6e1da;--card:#fff;--accent:#2f5d50;--up:#2f7d4f;--down:#b23b3b}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141311;--fg:#ece8e2;--muted:#9c958c;--line:#2c2925;--card:#1c1a17;--accent:#8fc1ae;--up:#6fc28f;--down:#e07a7a}}
:root[data-theme=dark]{--bg:#141311;--fg:#ece8e2;--muted:#9c958c;--line:#2c2925;--card:#1c1a17;--accent:#8fc1ae;--up:#6fc28f;--down:#e07a7a}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:680px;margin:0 auto;padding:20px 16px 64px}
header h1{font-size:26px;line-height:1.2;margin:4px 0 6px}
.date{color:var(--muted);font-size:14px;text-transform:uppercase;letter-spacing:.06em}
.lead{font-size:18px;margin:10px 0 0}
nav.toc{display:flex;gap:8px;overflow-x:auto;padding:14px 0;margin:0 -16px;padding-left:16px;scrollbar-width:none;position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:1}
nav.toc a{flex:none;font-size:14px;padding:5px 11px;border:1px solid var(--line);border-radius:999px;color:var(--fg);text-decoration:none}
section{padding-top:22px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent);margin:0 0 10px}
.item{padding:10px 0;border-bottom:1px solid var(--line)}.item:last-child{border:0}
.item h3{font-size:17px;margin:0 0 3px;line-height:1.35}
.item p{margin:0}
.src{font-size:13px;color:var(--muted);margin-top:4px}
a{color:var(--accent)}
.mk{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin-bottom:10px}
.mk div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.mk b{display:block;font-size:13px;color:var(--muted);font-weight:500}
.mk span{font-variant-numeric:tabular-nums}.up{color:var(--up)}.down{color:var(--down)}
.topic{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.topic .field{font-size:13px;color:var(--muted)}
footer{margin-top:36px;font-size:13px;color:var(--muted)}
ul.arch{list-style:none;padding:0}ul.arch li{padding:9px 0;border-bottom:1px solid var(--line)}
ul.arch a{text-decoration:none;font-weight:600}
"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def de_date(d):
    return f"{WD[d.weekday()]}, {d.day}. {MON[d.month - 1]} {d.year}"


def fmt_num(x):
    if x is None:
        return "–"
    s = f"{x:,.2f}" if x < 100 else f"{x:,.0f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def page(title, body):
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>"""


def render_day(c, raw):
    d = dt.date.fromisoformat(c["date"])
    secs = c.get("sections", [])
    toc = "".join(f'<a href="#{esc(s["id"])}">{esc(s["title"])}</a>' for s in secs)
    if c.get("topic"):
        toc += '<a href="#topic">Tagesthema</a>'
    out = [f'<header><div class="date">{de_date(d)}</div><h1>Morning Feed</h1>'
           f'<p class="lead">{esc(c.get("headline"))}</p></header><nav class="toc">{toc}</nav>']
    for s in secs:
        out.append(f'<section id="{esc(s["id"])}"><h2>{esc(s["title"])}</h2>')
        if s["id"] == "markets" and raw.get("markets"):
            cells = []
            for m in raw["markets"]:
                ch = m.get("change_pct")
                cls = "up" if ch and ch > 0 else "down" if ch and ch < 0 else ""
                sign = f"{ch:+.2f} %".replace(".", ",") if ch is not None else ""
                cells.append(f'<div><b>{esc(m["name"])}</b><span>{fmt_num(m["price"])}</span> '
                             f'<span class="{cls}">{sign}</span></div>')
            out.append(f'<div class="mk">{"".join(cells)}</div>')
        for it in s.get("items", []):
            src = esc(it.get("source"))
            link = f' · <a href="{esc(it["url"])}">Quelle</a>' if it.get("url") else ""
            out.append(f'<div class="item"><h3>{esc(it.get("title"))}</h3><p>{esc(it.get("summary"))}</p>'
                       f'<div class="src">{src}{link}</div></div>')
        out.append("</section>")
    t = c.get("topic")
    if t:
        links = " · ".join(f'<a href="{esc(u)}">mehr</a>' for u in t.get("links", []))
        out.append(f'<section id="topic"><h2>Tagesthema</h2><div class="topic"><div class="field">{esc(t.get("field"))}</div>'
                   f'<h3>{esc(t.get("title"))}</h3><p>{esc(t.get("body"))}</p><div class="src">{links}</div></div></section>')
    failed = raw.get("health", {}).get("failed", [])
    note = f'{len(failed)} Quelle(n) nicht erreichbar: {esc(", ".join(f["source"] for f in failed))}. ' if failed else ""
    out.append(f'<footer>{note}Kurse: Yahoo Finance, Stand Abruf. <a href="../">Archiv</a></footer>')
    return page(f"Morning Feed {d.isoformat()}", "".join(out))


def render_index():
    days = sorted((p.stem for p in (DOCS / "d").glob("*.html")), reverse=True)
    rows = []
    for ds in days:
        cj = ROOT / "content" / f"{ds}.json"
        head = json.loads(cj.read_text()).get("headline", "") if cj.exists() else ""
        rows.append(f'<li><a href="d/{ds}.html">{de_date(dt.date.fromisoformat(ds))}</a><div class="src">{esc(head)}</div></li>')
    latest = f'<p><a href="d/{days[0]}.html">Heute lesen →</a></p>' if days else ""
    body = f'<header><div class="date">Archiv</div><h1>Morning Feed</h1></header>{latest}<ul class="arch">{"".join(rows)}</ul>'
    (DOCS / "index.html").write_text(page("Morning Feed", body))


def telegram_text(c):
    d = dt.date.fromisoformat(c["date"])
    url = f"{BASE_URL}/d/{c['date']}.html"
    bullets = "\n".join(f"• {html.escape(b)}" for b in c.get("telegram_bullets", [])[:4])
    return (f"☀️ <b>Morning Feed · {WD[d.weekday()][:2]}, {d.day}.{d.month}.</b>\n\n"
            f"{html.escape(c.get('headline', ''))}\n\n{bullets}\n\n<a href=\"{url}\">Feed lesen</a>")


def no_dashes(x):
    """Hausregel: keine Gedankenstriche als Satzzeichen."""
    if isinstance(x, str):
        return x.replace(" – ", ", ").replace(" — ", ", ").replace("—", ", ")
    if isinstance(x, list):
        return [no_dashes(i) for i in x]
    if isinstance(x, dict):
        return {k: (v if k in ("url", "links", "date", "id") else no_dashes(v)) for k, v in x.items()}
    return x


def main():
    cpath = Path(sys.argv[1])
    c = no_dashes(json.loads(cpath.read_text()))
    raw_path = ROOT / "work" / "raw.json"
    raw = json.loads(raw_path.read_text()) if raw_path.exists() else {}
    (DOCS / "d").mkdir(parents=True, exist_ok=True)
    (DOCS / "d" / f"{c['date']}.html").write_text(render_day(c, raw))
    (DOCS / ".nojekyll").write_text("")
    (DOCS / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    render_index()
    (ROOT / "work").mkdir(exist_ok=True)
    (ROOT / "work" / "telegram.txt").write_text(telegram_text(c))
    print(f"built docs/d/{c['date']}.html")


if __name__ == "__main__":
    main()
