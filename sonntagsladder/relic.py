"""Abruf der Spielhistorie bei Relic (oeffentlich, ohne Schluessel).

Relic liefert je Spieler nur die letzten 10 Spiele pro Modus, Custom Games
eingeschlossen. Aeltere Spiele gibt es nirgends mehr - deshalb muss
regelmaessig abgefragt und selbst gespeichert werden.
"""

from __future__ import annotations

import json
import urllib.request

URL = (
    "https://coh2-api.reliclink.com/community/leaderboard/"
    "getRecentMatchHistoryByProfileId?title=coh2&profile_id={profil_id}"
)
USER_AGENT = "coh2-sonntagsladder/1.0 (+https://github.com/gunther09/coh2sonntagsladder)"
TIMEOUT_SEKUNDEN = 20


class RelicFehler(RuntimeError):
    pass


def hole_spielhistorie(profil_id: int) -> dict:
    anfrage = urllib.request.Request(
        URL.format(profil_id=int(profil_id)),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(anfrage, timeout=TIMEOUT_SEKUNDEN) as antwort:
        daten = json.load(antwort)
    meldung = (daten.get("result") or {}).get("message")
    if meldung != "SUCCESS":
        raise RelicFehler(f"Relic antwortet fuer Profil {profil_id} mit {meldung!r}")
    return daten
