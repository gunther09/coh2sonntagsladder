"""Spiele aus der Relic-Antwort lesen und die Ladder rechnen.

Gewertet werden nur Custom Games (matchtype 0), an denen genau die vier
Spieler aus spieler.py teilgenommen haben, zwei gegen zwei, mit eindeutigem
Sieger. Abgebrochene Spiele (kein Team hat gewonnen) zaehlen nicht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .spieler import SPIELER, TEAMS, seite

MATCHTYPE_CUSTOM = 0
RESULT_NIEDERLAGE = 0
RESULT_SIEG = 1

_SPIELER_REIHENFOLGE = {profil_id: index for index, profil_id in enumerate(SPIELER)}


def _reihenfolge(profil_id: int) -> tuple[int, int]:
    return (_SPIELER_REIHENFOLGE.get(profil_id, len(_SPIELER_REIHENFOLGE)), profil_id)


def sortiertes_team(profil_ids: Iterable[int]) -> tuple[int, ...]:
    return tuple(sorted(profil_ids, key=_reihenfolge))


@dataclass(frozen=True)
class Teilnahme:
    profil_id: int
    team: int
    sieg: bool
    race_id: int


@dataclass(frozen=True)
class Spiel:
    id: int
    start: int  # Unix-Zeit
    ende: int  # Unix-Zeit
    karte: str  # Rohname von Relic, z.B. "4p_minsk_pocket"
    teilnahmen: tuple[Teilnahme, ...]

    @property
    def sieger(self) -> tuple[int, ...]:
        return sortiertes_team(t.profil_id for t in self.teilnahmen if t.sieg)

    @property
    def verlierer(self) -> tuple[int, ...]:
        return sortiertes_team(t.profil_id for t in self.teilnahmen if not t.sieg)

    @property
    def dauer_minuten(self) -> int:
        return max(0, round((self.ende - self.start) / 60))

    def race_id(self, profil_id: int) -> int | None:
        for teilnahme in self.teilnahmen:
            if teilnahme.profil_id == profil_id:
                return teilnahme.race_id
        return None

    def als_dict(self) -> dict:
        return {
            "id": self.id,
            "start": self.start,
            "ende": self.ende,
            "karte": self.karte,
            "teilnahmen": [
                {"profil_id": t.profil_id, "team": t.team, "sieg": t.sieg, "race_id": t.race_id}
                for t in self.teilnahmen
            ],
        }

    @classmethod
    def aus_dict(cls, daten: dict) -> "Spiel":
        return cls(
            id=int(daten["id"]),
            start=int(daten["start"]),
            ende=int(daten["ende"]),
            karte=str(daten.get("karte", "")),
            teilnahmen=tuple(
                Teilnahme(
                    profil_id=int(t["profil_id"]),
                    team=int(t["team"]),
                    sieg=bool(t["sieg"]),
                    race_id=int(t["race_id"]),
                )
                for t in daten["teilnahmen"]
            ),
        )


def spiele_aus_antwort(antwort: dict, spieler_ids: Iterable[int] = SPIELER) -> list[Spiel]:
    """Alle gewerteten Ladder-Spiele aus einer getRecentMatchHistoryByProfileId-Antwort."""
    gesucht = frozenset(spieler_ids)
    spiele = []
    for match in antwort.get("matchHistoryStats") or []:
        if match.get("matchtype_id") != MATCHTYPE_CUSTOM:
            continue
        berichte = match.get("matchhistoryreportresults") or []
        if len(berichte) != len(gesucht) or {b.get("profile_id") for b in berichte} != gesucht:
            continue

        teams: dict[int, list[dict]] = {}
        for bericht in berichte:
            teams.setdefault(bericht.get("teamid"), []).append(bericht)
        if len(teams) != 2 or any(len(mitglieder) != len(gesucht) // 2 for mitglieder in teams.values()):
            continue

        # Genau ein Team komplett Sieg, das andere komplett Niederlage.
        ergebnisse = sorted(
            tuple(sorted({b.get("resulttype") for b in mitglieder})) for mitglieder in teams.values()
        )
        if ergebnisse != [(RESULT_NIEDERLAGE,), (RESULT_SIEG,)]:
            continue

        try:
            spiele.append(
                Spiel(
                    id=int(match["id"]),
                    start=int(match["startgametime"]),
                    ende=int(match["completiontime"]),
                    karte=str(match.get("mapname") or ""),
                    teilnahmen=tuple(
                        Teilnahme(
                            profil_id=int(b["profile_id"]),
                            team=int(b["teamid"]),
                            sieg=b["resulttype"] == RESULT_SIEG,
                            race_id=int(b.get("race_id", -1)),
                        )
                        for b in sorted(berichte, key=lambda b: _reihenfolge(b["profile_id"]))
                    ),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return spiele


_KARTEN_PRAEFIX = re.compile(r"^\s*\d+\s*p?[_\s]+", re.IGNORECASE)
_KLEINE_WOERTER = {"of", "to", "the", "in", "on", "at", "am", "im"}


def kartenname(roh: str) -> str:
    """'4p_road_to_kharkov' -> 'Road to Kharkov', '4 duclair' -> 'Duclair'."""
    name = _KARTEN_PRAEFIX.sub("", roh or "").replace("_", " ").split()
    if not name:
        return roh or "?"
    woerter = [name[0].capitalize()] + [
        wort if wort in _KLEINE_WOERTER else wort.capitalize() for wort in name[1:]
    ]
    return " ".join(woerter)


def chronologisch(spiele: Iterable[Spiel]) -> list[Spiel]:
    return sorted(spiele, key=lambda s: (s.ende, s.id))


@dataclass
class Bilanz:
    verlauf: list[bool] = field(default_factory=list)  # chronologisch, True = Sieg

    @property
    def siege(self) -> int:
        return sum(self.verlauf)

    @property
    def niederlagen(self) -> int:
        return len(self.verlauf) - self.siege

    @property
    def spiele(self) -> int:
        return len(self.verlauf)

    @property
    def quote(self) -> float | None:
        return self.siege / self.spiele if self.verlauf else None

    @property
    def serie(self) -> tuple[bool, int] | None:
        """(True, 3) = drei Siege in Folge, (False, 2) = zwei Niederlagen in Folge."""
        if not self.verlauf:
            return None
        letzter = self.verlauf[-1]
        laenge = 0
        for ergebnis in reversed(self.verlauf):
            if ergebnis != letzter:
                break
            laenge += 1
        return letzter, laenge


def spielerbilanzen(spiele: Iterable[Spiel]) -> dict[int, Bilanz]:
    bilanzen = {profil_id: Bilanz() for profil_id in SPIELER}
    for spiel in chronologisch(spiele):
        for teilnahme in spiel.teilnahmen:
            bilanzen.setdefault(teilnahme.profil_id, Bilanz()).verlauf.append(teilnahme.sieg)
    return bilanzen


def teambilanzen(spiele: Iterable[Spiel]) -> dict[tuple[int, ...], Bilanz]:
    bilanzen: dict[tuple[int, ...], Bilanz] = {}
    for spiel in chronologisch(spiele):
        bilanzen.setdefault(spiel.sieger, Bilanz()).verlauf.append(True)
        bilanzen.setdefault(spiel.verlierer, Bilanz()).verlauf.append(False)
    return bilanzen


def _sortierschluessel(bilanz: Bilanz) -> tuple:
    if not bilanz.verlauf:
        return (1, 0.0, 0, 0)
    return (0, -bilanz.quote, -bilanz.siege, bilanz.niederlagen)


def rangliste(bilanzen: dict, *, schluessel_reihenfolge=None) -> list[tuple[int, object, Bilanz]]:
    """[(platz, schluessel, bilanz)], gleiche Bilanz = gleicher Platz."""
    nebenschluessel = schluessel_reihenfolge or (lambda schluessel: schluessel)
    geordnet = sorted(
        bilanzen.items(), key=lambda paar: (_sortierschluessel(paar[1]), nebenschluessel(paar[0]))
    )
    ergebnis = []
    for index, (schluessel, bilanz) in enumerate(geordnet):
        if ergebnis and _sortierschluessel(ergebnis[-1][2]) == _sortierschluessel(bilanz):
            platz = ergebnis[-1][0]
        else:
            platz = index + 1
        ergebnis.append((platz, schluessel, bilanz))
    return ergebnis


def spielerrangliste(spiele: Iterable[Spiel]) -> list[tuple[int, int, Bilanz]]:
    return rangliste(spielerbilanzen(spiele), schluessel_reihenfolge=_reihenfolge)


def teamrangliste(spiele: Iterable[Spiel]) -> list[tuple[int, tuple[int, ...], Bilanz]]:
    return rangliste(
        teambilanzen(spiele),
        schluessel_reihenfolge=lambda team: tuple(_reihenfolge(p) for p in team),
    )


def duell(spiele: Iterable[Spiel], team_a: tuple[int, ...], team_b: tuple[int, ...]) -> tuple[int, int]:
    """Direkter Vergleich genau dieser beiden Teams: (Siege A, Siege B)."""
    a, b = sortiertes_team(team_a), sortiertes_team(team_b)
    siege_a = siege_b = 0
    for spiel in spiele:
        if (spiel.sieger, spiel.verlierer) == (a, b):
            siege_a += 1
        elif (spiel.sieger, spiel.verlierer) == (b, a):
            siege_b += 1
    return siege_a, siege_b


# --- Das feste Duell: zwei Teams, Achse oder Alliierte -----------------------

GEMISCHT = "gemischt"


def team_seite(spiel: Spiel, team: Iterable[int]) -> str:
    """'Achse', 'Alliierte' oder 'gemischt' (z.B. Wehrmacht + USF im Custom Game)."""
    seiten = {seite(spiel.race_id(profil_id)) for profil_id in team}
    if len(seiten) == 1 and None not in seiten:
        return seiten.pop()
    return GEMISCHT


def ist_teamduell(spiel: Spiel, teams: tuple[tuple[int, ...], ...] = TEAMS) -> bool:
    """Spielen genau die beiden festen Teams gegeneinander?"""
    paarung = {frozenset(spiel.sieger), frozenset(spiel.verlierer)}
    return paarung == {frozenset(team) for team in teams}


def teamduelle(spiele: Iterable[Spiel], teams: tuple[tuple[int, ...], ...] = TEAMS) -> list[Spiel]:
    return [spiel for spiel in chronologisch(spiele) if ist_teamduell(spiel, teams)]


def sieger_index(spiel: Spiel, teams: tuple[tuple[int, ...], ...] = TEAMS) -> int:
    """0 oder 1: welches der festen Teams hat gewonnen."""
    return 0 if frozenset(spiel.sieger) == frozenset(teams[0]) else 1


@dataclass
class Duell:
    """Auswertung des festen Duells, Index 0/1 wie in TEAMS."""

    spiele: list[Spiel]
    bilanzen: tuple[Bilanz, Bilanz]
    # je Team: Seite -> Bilanz (nur Seiten, mit denen das Team gespielt hat)
    nach_seite: tuple[dict[str, Bilanz], dict[str, Bilanz]]
    # (Seite Team 0, Seite Team 1) -> [Siege Team 0, Siege Team 1]
    paarungen: dict[tuple[str, str], list[int]]
    # Seite -> [Siege, Spiele] ueber beide Teams, nur Spiele Achse gegen Alliierte
    seiten: dict[str, list[int]]


def duell_auswerten(spiele: Iterable[Spiel], teams: tuple[tuple[int, ...], ...] = TEAMS) -> Duell:
    duelle = teamduelle(spiele, teams)
    bilanzen = (Bilanz(), Bilanz())
    nach_seite: tuple[dict[str, Bilanz], dict[str, Bilanz]] = ({}, {})
    paarungen: dict[tuple[str, str], list[int]] = {}
    seiten = {"Achse": [0, 0], "Alliierte": [0, 0]}
    for spiel in duelle:
        gewinner = sieger_index(spiel, teams)
        team_seiten = tuple(team_seite(spiel, team) for team in teams)
        for index in (0, 1):
            sieg = index == gewinner
            bilanzen[index].verlauf.append(sieg)
            nach_seite[index].setdefault(team_seiten[index], Bilanz()).verlauf.append(sieg)
        paarungen.setdefault(team_seiten, [0, 0])[gewinner] += 1
        if set(team_seiten) == {"Achse", "Alliierte"}:
            for index in (0, 1):
                eintrag = seiten[team_seiten[index]]
                eintrag[1] += 1
                eintrag[0] += index == gewinner
    return Duell(duelle, bilanzen, nach_seite, paarungen, seiten)
