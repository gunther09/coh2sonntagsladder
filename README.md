# CoH2-Sonntagsladder

Rangliste für vier feste Spieler, die in **Company of Heroes 2** regelmäßig
2 vs 2 gegeneinander spielen (Custom Games). Die Ergebnisse erscheinen
automatisch in einem Discord-Kanal.

## Wie es funktioniert

- Jeden Montag um 7 Uhr (und sofort per `/ladder` in Discord, über den
  Elternabend-Bot) fragt ein systemd-Timer die öffentliche Relic-Schnittstelle
  ab (`getRecentMatchHistoryByProfileId`, ohne Schlüssel) – je Spieler.
- Gewertet wird nur ein **Custom Game mit genau diesen vier Spielern**,
  zwei gegen zwei, mit eindeutigem Sieger. Automatch, Spiele mit anderen
  Leuten und abgebrochene Spiele zählen nicht. Die vier stehen in
  [`sonntagsladder/spieler.py`](sonntagsladder/spieler.py).
- Neue Spiele werden in einer JSON-Datei gespeichert und per **Discord-Webhook**
  gemeldet. Eine **Ranglisten-Nachricht** im Kanal wird bei jedem Lauf
  aktualisiert (einmal von Hand anheften).
- Gezeigt wird nur das Duell der zwei festen Teams (**Ace & DiplomAgronom**
  gegen **Bella & UBack**, in `spieler.TEAMS`), als Discord-Embeds: oben die
  Gesamtwertung mit Serie und Verlauf, dann **Achse oder Alliierte** (wer
  gewinnt mit welcher Seite, Stand je Paarung), unten die letzten Spiele als
  Tabelle. Spiele in anderer Besetzung werden gespeichert, aber nicht gezeigt.

**Grenze:** Relic hält je Spieler nur die letzten 10 Spiele pro Modus. Was
älter ist, gibt es nirgends mehr (auch coh2stats.com zeigt Custom Games
nicht). Die Ladder beginnt deshalb mit den Spielen, die beim ersten Lauf
noch abrufbar waren, und wächst ab dann.

Zur Laufzeit wird nur die Python-Standardbibliothek gebraucht (3.10+), kein
venv, keine Pakete.

## Lokal

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest                    # Schnelltest, offline
.venv\Scripts\python.exe -m sonntagsladder --trocken  # echte Daten holen, nur anzeigen
```

`--zeigen` gibt die Rangliste aus den gespeicherten Spielen aus (Ordner aus
`COH2_DATEN`, Vorgabe `./daten`).

## Betrieb auf dem Pi

| Was | Wo |
|---|---|
| Code | `/opt/coh2-sonntagsladder/app/sonntagsladder` |
| Spiele und Zustand | `/var/lib/coh2-sonntagsladder/zustand.json` – **das einzig Unersetzliche** |
| Webhook-URL (geheim) | `/etc/coh2-sonntagsladder/webhook.env`, root-only, nie im Repo |
| Dienst / Timer | `coh2-sonntagsladder.service` (oneshot), `coh2-sonntagsladder.timer` (montags 7 Uhr) |
| Benutzer | `coh2ladder` (Systembenutzer ohne Login) |

```bash
bash deploy/push.sh        # Git Bash am PC: Tests, Code auf den Pi, sofort ein Lauf
bash deploy/webhook.sh     # Webhook-URL setzen/ersetzen (verdeckte Eingabe)
```

Auf dem Pi:

```bash
journalctl -u coh2-sonntagsladder -n 20            # letzte Läufe
systemctl list-timers coh2-sonntagsladder.timer    # nächster Lauf
sudo systemctl start coh2-sonntagsladder           # sofort laufen lassen
```

**Ranglisten-Nachricht gelöscht?** Kein Problem: Der nächste Lauf sendet eine
neue (im Log steht ihre ID), die dann wieder angeheftet wird.

**Neuer Webhook / anderer Kanal:** `bash deploy/webhook.sh`, dann in
`zustand.json` den Wert `ranglisten_nachricht` auf `null` setzen – sonst
versucht der Dienst, die alte Nachricht über den neuen Webhook zu bearbeiten,
bekommt „nicht gefunden“ und sendet ohnehin neu.
