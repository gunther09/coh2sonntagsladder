"""Ein Lauf: bei Relic nachsehen, neue Spiele speichern, in Discord melden,
Ranglisten-Nachricht aktualisieren. Der Timer auf dem Pi startet das alle
15 Minuten.

Reihenfolge mit Absicht: Erst werden neue Spiele gespeichert, dann wird
gemeldet. Faellt Discord aus, sind die Spiele trotzdem gesichert, und der
naechste Lauf holt die Meldung nach.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable

from . import ausgabe, liga, relic, webhook
from .speicher import Speicher
from .spieler import SPIELER, name

log = logging.getLogger("sonntagsladder")


class AbrufFehler(RuntimeError):
    """Relic war fuer keinen der vier Spieler erreichbar."""


@dataclass
class Ergebnis:
    neu: int
    gesamt: int
    gemeldet: int
    rangliste: str  # "aktualisiert", "neu gesendet" oder "ohne Webhook"


def hole_spiele(hole: Callable[[int], dict] = relic.hole_spielhistorie) -> dict[int, liga.Spiel]:
    """Alle Ladder-Spiele aus der Relic-Historie der vier Spieler, ohne Duplikate.

    Alle vier fragen, nicht nur einen: Wer nebenbei andere Custom Games spielt,
    schiebt die Ladder-Spiele schneller aus seinen letzten 10 heraus."""
    gefunden: dict[int, liga.Spiel] = {}
    fehler = []
    for profil_id in SPIELER:
        try:
            for spiel in liga.spiele_aus_antwort(hole(profil_id)):
                gefunden[spiel.id] = spiel
        except Exception as e:  # ein Spieler darf ausfallen, alle nicht
            fehler.append(f"{name(profil_id)}: {e}")
    if len(fehler) == len(SPIELER):
        raise AbrufFehler("Relic-Abruf fuer alle Spieler fehlgeschlagen: " + "; ".join(fehler))
    for meldung in fehler:
        log.warning("Relic-Abruf fehlgeschlagen fuer %s", meldung)
    return gefunden


def lauf(
    speicher: Speicher,
    *,
    webhook_url: str | None,
    hole: Callable[[int], dict] = relic.hole_spielhistorie,
    senden: Callable[[str, str], str] = webhook.senden,
    bearbeiten: Callable[[str, str, str], None] = webhook.bearbeiten,
    jetzt: Callable[[], float] = time.time,
) -> Ergebnis:
    zustand = speicher.laden()
    erstlauf = zustand.neu_angelegt

    neu = [s for i, s in hole_spiele(hole).items() if i not in zustand.spiele]
    for spiel in neu:
        zustand.spiele[spiel.id] = spiel
    if erstlauf:
        # Der Bestand beim allerersten Lauf wird nicht einzeln gemeldet,
        # er steht nur in der Rangliste.
        zustand.gemeldet.update(zustand.spiele)
    speicher.speichern(zustand)

    if not webhook_url:
        return Ergebnis(len(neu), len(zustand.spiele), 0, "ohne Webhook")

    offen = liga.chronologisch(s for i, s in zustand.spiele.items() if i not in zustand.gemeldet)
    if offen:
        senden(webhook_url, ausgabe.neue_spiele_text(offen, zustand.spiele.values()))
        zustand.gemeldet.update(s.id for s in offen)
        speicher.speichern(zustand)

    text = ausgabe.ranglisten_text(zustand.spiele.values(), int(jetzt()))
    status = "aktualisiert"
    if zustand.ranglisten_nachricht:
        try:
            bearbeiten(webhook_url, zustand.ranglisten_nachricht, text)
        except webhook.NachrichtFehlt:
            log.warning("Ranglisten-Nachricht %s gibt es nicht mehr, sende neu", zustand.ranglisten_nachricht)
            zustand.ranglisten_nachricht = None
    if not zustand.ranglisten_nachricht:
        zustand.ranglisten_nachricht = senden(webhook_url, text)
        speicher.speichern(zustand)
        status = "neu gesendet"
        log.info(
            "Neue Ranglisten-Nachricht %s gesendet - bitte in Discord anheften",
            zustand.ranglisten_nachricht,
        )

    return Ergebnis(len(neu), len(zustand.spiele), len(offen), status)
