"""Aufruf:

    python -m sonntagsladder            ein Lauf (holen, speichern, melden)
    python -m sonntagsladder --trocken  nur holen und anzeigen, nichts speichern oder senden
    python -m sonntagsladder --zeigen   Rangliste aus den gespeicherten Spielen anzeigen

Umgebung:
    COH2_DATEN        Ordner fuer zustand.json (Vorgabe: ./daten)
    COH2_WEBHOOK_URL  Discord-Webhook; ohne ihn wird nur gesammelt
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from . import ausgabe, liga, webhook
from .lauf import hole_spiele, lauf
from .speicher import Speicher

log = logging.getLogger("sonntagsladder")


def _konsole_utf8() -> None:
    # Windows-Konsole: Emojis und Umlaute in der Vorschau nicht am Codepage scheitern lassen
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sonntagsladder", description="CoH2-Sonntagsladder")
    modus = parser.add_mutually_exclusive_group()
    modus.add_argument("--trocken", action="store_true", help="nur holen und anzeigen")
    modus.add_argument("--zeigen", action="store_true", help="gespeicherte Rangliste anzeigen")
    args = parser.parse_args(argv)

    _konsole_utf8()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    speicher = Speicher(os.environ.get("COH2_DATEN") or "daten")

    if args.zeigen:
        print(ausgabe.ranglisten_text(speicher.laden().spiele.values(), int(time.time())))
        return 0

    if args.trocken:
        spiele = liga.chronologisch(hole_spiele().values())
        print(f"{len(spiele)} Ladder-Spiele bei Relic gefunden\n")
        if spiele:
            print(ausgabe.neue_spiele_text(spiele[-1:], spiele))
            print()
        print(ausgabe.ranglisten_text(spiele, int(time.time())))
        return 0

    exitcode = 0
    url = os.environ.get("COH2_WEBHOOK_URL", "").strip() or None
    if url:
        try:
            url = webhook.pruefe_url(url)
        except webhook.WebhookFehler as e:
            log.error("%s - sammle nur, ohne zu melden", e)
            url, exitcode = None, 1

    try:
        ergebnis = lauf(speicher, webhook_url=url)
    except Exception as e:  # kurze Zeile ins Journal, kein Traceback mit Interna
        log.error("Lauf fehlgeschlagen: %s: %s", type(e).__name__, e)
        return 1

    log.info(
        "%d neu, %d gesamt, %d gemeldet, Rangliste %s",
        ergebnis.neu, ergebnis.gesamt, ergebnis.gemeldet, ergebnis.rangliste,
    )
    return exitcode


if __name__ == "__main__":
    sys.exit(main())
