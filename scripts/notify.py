#!/usr/bin/env python3
"""Send a Telegram message. Usage:
  notify.py work/telegram.txt        (HTML-formatted file)
  notify.py --text "⚠️ plain text"   (error alerts, nur an die erste Chat-ID)
Needs env TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (kommagetrennt fuer mehrere
Empfaenger oder einen Kanal wie @name). Exit 1 if any send fails.
"""
import json
import os
import sys
import urllib.parse
import urllib.request


def send(msg, parse_html, chat):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
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
    print(f"telegram sent to {chat}")


if __name__ == "__main__":
    chats = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not chats:
        sys.exit("TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID fehlt")
    if len(sys.argv) >= 3 and sys.argv[1] == "--text":
        send(" ".join(sys.argv[2:]), False, chats[0])
    else:
        msg = open(sys.argv[1], encoding="utf-8").read()
        for c in chats:
            send(msg, True, c)
