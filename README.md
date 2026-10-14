# Morning Feed

Persönlicher Morgen-Feed (Mo–Fr). Eine Claude-Cloud-Routine folgt `ROUTINE.md`:
`scripts/fetch.py` sammelt Quellen aus `sources.json`, Claude schreibt `content/<Datum>.json`,
`scripts/build.py` rendert nach `docs/` (GitHub Pages, Branch `claude/feed`), `scripts/notify.py` schickt den Link per Telegram.
`.github/workflows/watchdog.yml` meldet, wenn der Feed bis 08:30 (Sommerzeit) fehlt.

Quellen ändern: `sources.json` bearbeiten (YouTube-Kandidaten liegen unter `youtube_candidates_inactive`).
