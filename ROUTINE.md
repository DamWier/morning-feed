# Morning Feed: Anleitung für den Routine-Lauf

Du erstellst den persönlichen Morning Feed für Damian (Berlin, Gründer von vier DTC-Marken für
Supplements und Kosmetik in DACH). Er liest ihn morgens am Handy, ca. 5 Minuten Lesezeit.
Arbeite ohne Rückfragen. Jeder Fehler wird gemeldet, nie verschwiegen.

## Fehlerregel (gilt für jeden Schritt)

Schlägt ein Schritt fehl, den du nicht innerhalb von zwei Versuchen behebst:
1. `python3 scripts/notify.py --text "⚠️ Morning Feed <Datum>: <Schritt> fehlgeschlagen. <Fehler in einem Satz>"`
2. Zusätzlich das Tool `PushNotification` mit derselben Meldung (auch wenn Telegram geklappt hat).
3. Abbrechen. Kein halber Feed, keine erfundenen Inhalte.

## Ablauf

1. `git checkout claude/feed && git pull --ff-only` (Branch `claude/feed` ist der Pages-Branch).
2. `pip install -q youtube-transcript-api` (Fehlschlag ist okay, dann gibt es Beschreibungen statt Transkripten).
3. Datum = heute in Europe/Berlin (`TZ=Europe/Berlin date +%F`). Existiert `content/<Datum>.json` schon, nur Schritt 7 bis 9 ausführen.
4. `python3 scripts/fetch.py` → `work/raw.json`. Exit-Code 2 heißt: fast alle Quellen tot, Fehlerregel anwenden.
5. Lies `work/raw.json` vollständig und die `topic`-Felder der letzten 30 Dateien in `content/`.
6. Schreibe `content/<Datum>.json` nach dem Schema unten.
7. `python3 scripts/build.py content/<Datum>.json`
8. `git add content docs && git commit -m "feed <Datum>" && git push origin claude/feed`
9. `python3 scripts/notify.py work/telegram.txt`
10. Wenn in `raw.json` unter `health.failed` mehr als 3 Quellen stehen: zusätzlich
    `notify.py --text "ℹ️ Morning Feed: <n> Quellen nicht erreichbar: <Namen>"`.
11. Schlusssatz der Session: Anzahl Meldungen, Videos, fehlgeschlagene Quellen.

## Schema `content/<Datum>.json`

```json
{
  "date": "YYYY-MM-DD",
  "headline": "Ein Satz: das Wichtigste des Tages.",
  "telegram_bullets": ["3 bis 4 kurze Zeilen, die wichtigsten Punkte über alle Rubriken"],
  "sections": [
    {"id": "youtube", "title": "YouTube", "items": [{"title": "", "summary": "", "source": "Kanal", "url": ""}]},
    {"id": "berlin", "title": "Berlin", "items": []},
    {"id": "germany", "title": "Deutschland", "items": []},
    {"id": "europe", "title": "Europa", "items": []},
    {"id": "world", "title": "Welt", "items": []},
    {"id": "markets", "title": "Märkte & Makro", "items": []},
    {"id": "ecom", "title": "E-Com, Deals & M&A", "items": []},
    {"id": "industry", "title": "Supplements & Beauty", "items": []},
    {"id": "ai", "title": "AI & Tech", "items": []}
  ],
  "topic": {"field": "", "title": "", "body": "", "links": [""]}
}
```

## Redaktionelle Regeln

- **Nur Fakten aus `raw.json`.** Jede Meldung hat die `url` eines Items aus raw.json. Nichts dazuerfinden.
- **Gleiche Story aus mehreren Quellen = eine Meldung**, die verlässlichste Quelle verlinken
  (Agentur/ÖR/Qualitätspresse vor Boulevard).
- **Sprache = Sprache der Quelle** (deutsche Quelle deutsch, englische englisch).
- **Pro Rubrik 3 bis 5 Meldungen**, je Meldung Titel (eigene Formulierung, max. 12 Wörter) plus
  1 bis 2 Sätze, was passiert ist und warum es zählt. Gesamt ca. 900 bis 1.100 Wörter.
  Ist eine Rubrik leer, weglassen.
- **Berlin:** Landespolitik, Verwaltung, Verkehr, Wirtschaft. Polizeimeldungen und Blaulicht nur, wenn wirklich groß.
- **Märkte & Makro:** Die Kurskacheln rendert build.py selbst. Du schreibst 3 bis 4 Meldungen zu
  Inflation, Zinsen, EZB/Fed, Konjunktur, großen Kursbewegungen. Zahlen exakt aus der Quelle.
- **E-Com, Deals & M&A:** Finanzierungsrunden, Übernahmen, Exits mit Betrag und Käufer/Investor.
  DACH und Europa bevorzugt, Consumer/DTC/Retail vor B2B-SaaS.
- **Supplements & Beauty:** Regulatorik (EFSA, BfR, EU), Markttrends, große Marken-Deals.
- **YouTube:** jedes Video aus `raw.youtube` einzeln, 3 bis 5 Sätze Kernaussage und Takeaways aus
  dem Transkript. Ohne Transkript aus der Beschreibung und mit dem Zusatz „(aus der Videobeschreibung)".
  Keine neuen Videos: Rubrik weglassen.
- **Tagesthema:** ein Konzept, Begriff, historisches Ereignis oder Fun Fact, das Damian noch nicht
  kennen muss. Feld rotieren durch `topic_fields` in raw.json, kein Feld zweimal in Folge, kein Thema
  aus den letzten 30 Tagen wiederholen. 120 bis 180 Wörter, deutsch, verständlich, mit einem
  konkreten Beispiel. Hier darfst du eigenes Wissen nutzen, aber nur gesicherte Fakten, und
  1 bis 2 seriöse Links (Wikipedia, Fachquelle) angeben.
- **Ton:** sachlich, warm, keine Gedankenstriche als Satzzeichen, kein Clickbait, keine Wertungen
  zu Parteien.
