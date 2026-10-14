#!/usr/bin/env python3
"""Send a Telegram message. Usage:
  notify.py work/telegram.txt        (HTML-formatted file)
  notify.py --text "⚠️ plain text"   (error alerts)
Needs env TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. Exit 1 on failure.
"""
import json
import os
import sys
import urllib.parse
import urllib.request


def send(msg, parse_html):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        sys.exit("TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID fehlt")
    data = {"chat_id": chat, "text": msg[:4000], "disable_web_page_preview": "true"}
    if parse_html:
        data["parse_mode"] = "HTML"
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = json.loads(r.read()).get("ok")
    except Exception as e:
        sys.exit(f"Telegram-Versand fehlgeschlagen: {type(e).__name__}")
    if not ok:
        sys.exit("Telegram-Versand fehlgeschlagen: ok=false")
    print("telegram sent")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--text":
        send(" ".join(sys.argv[2:]), parse_html=False)
    else:
        send(open(sys.argv[1], encoding="utf-8").read(), parse_html=True)
