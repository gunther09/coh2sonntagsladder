"""Zustand als eine JSON-Datei: alle je gesehenen Spiele, welche davon schon in
Discord gemeldet sind, und die ID der Ranglisten-Nachricht.

Die Spiele sind das Einzige, was sich nicht wiederbeschaffen laesst (Relic
vergisst sie nach 10 neueren Spielen). Geschrieben wird deshalb atomar:
erst eine temporaere Datei, dann umbenennen - ein Absturz mitten im Schreiben
laesst die alte Datei heil.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .liga import Spiel

DATEINAME = "zustand.json"
VERSION = 1


@dataclass
class Zustand:
    spiele: dict[int, Spiel] = field(default_factory=dict)
    gemeldet: set[int] = field(default_factory=set)
    ranglisten_nachricht: str | None = None
    neu_angelegt: bool = False  # Datei gab es noch nicht

    def als_dict(self) -> dict:
        return {
            "version": VERSION,
            "spiele": [self.spiele[i].als_dict() for i in sorted(self.spiele, key=lambda i: (self.spiele[i].ende, i))],
            "gemeldet": sorted(self.gemeldet),
            "ranglisten_nachricht": self.ranglisten_nachricht,
        }


class Speicher:
    def __init__(self, ordner: Path | str):
        self.ordner = Path(ordner)
        self.datei = self.ordner / DATEINAME

    def laden(self) -> Zustand:
        if not self.datei.exists():
            return Zustand(neu_angelegt=True)
        daten = json.loads(self.datei.read_text(encoding="utf-8"))
        if daten.get("version") != VERSION:
            raise ValueError(f"{self.datei}: unbekannte Version {daten.get('version')!r}")
        spiele = {}
        for eintrag in daten.get("spiele", []):
            spiel = Spiel.aus_dict(eintrag)
            spiele[spiel.id] = spiel
        return Zustand(
            spiele=spiele,
            gemeldet={int(i) for i in daten.get("gemeldet", [])},
            ranglisten_nachricht=daten.get("ranglisten_nachricht"),
        )

    def speichern(self, zustand: Zustand) -> None:
        self.ordner.mkdir(parents=True, exist_ok=True)
        inhalt = json.dumps(zustand.als_dict(), ensure_ascii=False, indent=1)
        fd, tmp = tempfile.mkstemp(prefix=".zustand-", suffix=".json", dir=self.ordner)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as datei:
                datei.write(inhalt)
                datei.flush()
                os.fsync(datei.fileno())
            os.replace(tmp, self.datei)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise
        zustand.neu_angelegt = False
