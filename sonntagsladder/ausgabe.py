"""Nachrichten fuer Discord: die angeheftete Ranglisten-Nachricht und die
Meldung zu neuen Spielen, beide als Embeds.

Gezeigt wird nur das feste Duell der beiden Teams aus spieler.TEAMS: oben die
Gesamtwertung, dann Achse gegen Alliierte, unten die letzten Spiele.

Eine Nachricht ist ein dict im Format der Discord-Webhook-API
({"content": ..., "embeds": [...]}); webhook.py schickt es unveraendert.
Discord-Grenzen: Beschreibung 4096, Feldwert 1024, alles zusammen 6000 Zeichen.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from . import liga
from .spieler import TEAM_EMOJI, TEAM_FARBE, TEAMS, kurzname, name

TITEL = "🏆 CoH2-Sonntagsladder"
LETZTE_SPIELE = 10
VERLAUF_MAX = 20
NEUE_SPIELE_MAX = 10
KARTE_MAX = 16
FARBE_NEUTRAL = 0x6B7280
# Den Befehl stellt der Elternabend-Bot im selben Server bereit (Repo DiscordBot),
# er startet nur den Dienst dieser Ladder auf dem Pi.
AKTUALISIEREN = "Sofort aktualisieren: /ladder"

EMBED_GESAMT = 6000
BESCHREIBUNG_MAX = 4096
FELDWERT_MAX = 1024

try:
    from zoneinfo import ZoneInfo

    _ZEITZONE = ZoneInfo("Europe/Berlin")
except Exception:  # Windows ohne tzdata: lokale Zeit des Rechners
    _ZEITZONE = None


def _zeit(unix: int) -> datetime:
    moment = datetime.fromtimestamp(unix, tz=timezone.utc)
    return moment.astimezone(_ZEITZONE) if _ZEITZONE else moment.astimezone()


def datum_zeit(unix: int) -> str:
    return _zeit(unix).strftime("%d.%m. %H:%M")


def datum(unix: int) -> str:
    return _zeit(unix).strftime("%d.%m.%Y")


def _markdown(text: str) -> str:
    for zeichen in ("\\", "*", "_", "~", "|", "`", ">", "#"):
        text = text.replace(zeichen, "\\" + zeichen)
    return text


def teamname(team: Iterable[int]) -> str:
    """'Ace & DiplomAgronom' (ohne Markdown)."""
    return " & ".join(name(profil_id) for profil_id in team)


def kurzer_teamname(team: Iterable[int]) -> str:
    """'Ace+Diplom' fuer die Tabelle."""
    return "+".join(kurzname(profil_id) for profil_id in team)


def _team(index: int, *, fett: bool = True) -> str:
    text = _markdown(teamname(TEAMS[index]))
    return f"{TEAM_EMOJI[index]} **{text}**" if fett else f"{TEAM_EMOJI[index]} {text}"


def _prozent(siege: int, spiele: int) -> str:
    return "–" if not spiele else f"{siege * 100 / spiele:.0f} %"


def _serie(bilanz: liga.Bilanz) -> str:
    serie = bilanz.serie
    if serie is None:
        return "–"
    sieg, laenge = serie
    if sieg:
        return "1 Sieg" if laenge == 1 else f"{laenge} Siege in Folge"
    return "1 Niederlage" if laenge == 1 else f"{laenge} Niederlagen in Folge"


def _kuerzen(text: str, laenge: int) -> str:
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def _tabelle(kopf: list[str], zeilen: list[list[str]]) -> str:
    breiten = [max(len(str(z[i])) for z in [kopf, *zeilen]) for i in range(len(kopf))]

    def zeile(werte):
        return "  ".join(str(w).ljust(breiten[i]) for i, w in enumerate(werte)).rstrip()

    return "```\n" + "\n".join([zeile(kopf), *(zeile(z) for z in zeilen)]) + "\n```"


def _fuss(duell: liga.Duell, jetzt: int) -> dict:
    teile = []
    if duell.spiele:
        teile.append(f"{len(duell.spiele)} Spiele seit {datum(duell.spiele[0].ende)}")
    teile += [f"Stand {datum_zeit(jetzt)}", "automatisch montags 7 Uhr", AKTUALISIEREN]
    return {"text": " · ".join(teile)}


# --- Ranglisten-Nachricht ----------------------------------------------------


def _gesamt_embed(duell: liga.Duell) -> dict:
    a, b = duell.bilanzen
    if a.siege == b.siege:
        fuehrung, farbe = "Gleichstand.", FARBE_NEUTRAL
    else:
        vorne = 0 if a.siege > b.siege else 1
        abstand = abs(a.siege - b.siege)
        fuehrung = f"{_team(vorne)} führen mit {abstand} {'Sieg' if abstand == 1 else 'Siegen'} Vorsprung."
        farbe = TEAM_FARBE[vorne]

    felder = [
        {
            "name": f"{TEAM_EMOJI[i]} {teamname(TEAMS[i])}",
            "value": f"**{bilanz.siege}** Siege · {_prozent(bilanz.siege, bilanz.spiele)}\n"
                     f"Serie: {_serie(bilanz)}",
            "inline": True,
        }
        for i, bilanz in enumerate(duell.bilanzen)
    ]
    letzte = duell.spiele[-VERLAUF_MAX:]
    felder.append({
        "name": f"Verlauf · letzte {len(letzte)}, neuestes rechts",
        "value": "".join(TEAM_EMOJI[liga.sieger_index(s)] for s in letzte),
        "inline": False,
    })
    return {
        "title": f"{TITEL} · Gesamtwertung",
        "description": f"## {TEAM_EMOJI[0]}  {a.siege} : {b.siege}  {TEAM_EMOJI[1]}\n{fuehrung}",
        "color": farbe,
        "fields": felder,
    }


_SEITEN_TITEL = {"Achse": "Mit Achse", "Alliierte": "Mit Alliierten", liga.GEMISCHT: "Gemischt"}


def _seiten_embed(duell: liga.Duell) -> dict:
    felder = []
    for seite_name in ("Achse", "Alliierte", liga.GEMISCHT):
        eintraege = [
            (i, duell.nach_seite[i][seite_name]) for i in (0, 1) if seite_name in duell.nach_seite[i]
        ]
        if not eintraege:
            continue
        # Rangliste je Seite: bessere Quote zuerst, bei Gleichstand Reihenfolge aus TEAMS
        eintraege.sort(key=lambda paar: (-(paar[1].quote or 0), -paar[1].siege, paar[0]))
        felder.append({
            "name": _SEITEN_TITEL[seite_name],
            "value": "\n".join(
                f"{TEAM_EMOJI[i]} **{b.siege}** von {b.spiele} · {_prozent(b.siege, b.spiele)}"
                for i, b in eintraege
            ),
            "inline": True,
        })

    paarungen = []
    for (seite_a, seite_b), (siege_a, siege_b) in sorted(
        duell.paarungen.items(), key=lambda paar: -sum(paar[1])
    ):
        paarungen.append(
            f"{TEAM_EMOJI[0]} {seite_a} gegen {TEAM_EMOJI[1]} {seite_b}: **{siege_a} : {siege_b}**"
        )
    if paarungen:
        felder.append({"name": "Paarungen", "value": "\n".join(paarungen), "inline": False})

    achse, alliierte = duell.seiten["Achse"], duell.seiten["Alliierte"]
    if achse[1]:
        felder.append({
            "name": "Welche Seite gewinnt?",
            "value": f"Achse {achse[0]} · Alliierte {alliierte[0]} "
                     f"(von {achse[1]} Spielen Achse gegen Alliierte)",
            "inline": False,
        })
    return {"title": "⚔️ Achse oder Alliierte", "color": FARBE_NEUTRAL, "fields": felder}


def letzte_spiele_tabelle(duell: liga.Duell, anzahl: int = LETZTE_SPIELE) -> str:
    zeilen = []
    for spiel in reversed(duell.spiele[-anzahl:]):
        zeilen.append([
            _zeit(spiel.ende).strftime("%d.%m."),
            kurzer_teamname(TEAMS[liga.sieger_index(spiel)]),
            liga.team_seite(spiel, spiel.sieger),
            _kuerzen(liga.kartenname(spiel.karte), KARTE_MAX),
        ])
    return _tabelle(["Datum", "Sieger", "als", "Karte"], zeilen)


def _letzte_embed(duell: liga.Duell, jetzt: int, anzahl: int) -> dict:
    return {
        "title": "📜 Letzte Spiele",
        "description": letzte_spiele_tabelle(duell, anzahl),
        "color": FARBE_NEUTRAL,
        "footer": _fuss(duell, jetzt),
    }


def embed_laenge(embed: dict) -> int:
    """So zaehlt Discord fuer die 6000-Zeichen-Grenze."""
    laenge = len(embed.get("title", "")) + len(embed.get("description", ""))
    laenge += len(embed.get("footer", {}).get("text", ""))
    for feld in embed.get("fields", []):
        laenge += len(feld["name"]) + len(feld["value"])
    return laenge


def ranglisten_nachricht(spiele: Iterable[liga.Spiel], jetzt: int) -> dict:
    duell = liga.duell_auswerten(spiele)
    if not duell.spiele:
        return {"content": "", "embeds": [{
            "title": TITEL,
            "description": f"Noch keine Spiele erfasst. Sobald {_team(0)} und {_team(1)} ein "
                           "Custom Game gegeneinander beendet haben, steht es hier.",
            "color": FARBE_NEUTRAL,
            "footer": _fuss(duell, jetzt),
        }]}

    for anzahl in range(LETZTE_SPIELE, 0, -1):
        embeds = [_gesamt_embed(duell), _seiten_embed(duell), _letzte_embed(duell, jetzt, anzahl)]
        if sum(map(embed_laenge, embeds)) <= EMBED_GESAMT:
            break
    return {"content": "", "embeds": embeds}


# --- Meldung neuer Spiele ----------------------------------------------------


def neue_spiele_nachricht(neue: Iterable[liga.Spiel], alle: Iterable[liga.Spiel]) -> dict | None:
    """None, wenn unter den neuen Spielen kein Duell der beiden Teams ist."""
    neue = liga.teamduelle(neue)
    if not neue:
        return None
    duell = liga.duell_auswerten(alle)

    zeilen = []
    for spiel in neue[:NEUE_SPIELE_MAX]:
        gewinner = liga.sieger_index(spiel)
        verlierer = 1 - gewinner
        zeilen.append(
            f"{_team(gewinner)} ({liga.team_seite(spiel, TEAMS[gewinner])}) schlagen "
            f"{_team(verlierer, fett=False)} ({liga.team_seite(spiel, TEAMS[verlierer])})"
        )
        zeilen.append(
            f"-# {datum_zeit(spiel.ende)} · {liga.kartenname(spiel.karte)} · {spiel.dauer_minuten} min"
        )
    if len(neue) > NEUE_SPIELE_MAX:
        zeilen.append(f"… und {len(neue) - NEUE_SPIELE_MAX} weitere")

    a, b = duell.bilanzen
    zeilen.append(f"\nGesamtstand: {TEAM_EMOJI[0]} **{a.siege} : {b.siege}** {TEAM_EMOJI[1]}")
    return {"content": "", "embeds": [{
        "title": "⚔️ Neues Spiel" if len(neue) == 1 else f"⚔️ {len(neue)} neue Spiele",
        "description": "\n".join(zeilen)[:BESCHREIBUNG_MAX],
        "color": TEAM_FARBE[liga.sieger_index(neue[-1])],
    }]}


# --- Vorschau in der Konsole -------------------------------------------------


def als_text(nachricht: dict) -> str:
    """Grobe Textfassung einer Nachricht, fuer --zeigen/--trocken und Tests."""
    teile = [nachricht.get("content") or ""]
    for embed in nachricht.get("embeds", []):
        teile.append(f"== {embed.get('title', '')} ==")
        if embed.get("description"):
            teile.append(embed["description"])
        for feld in embed.get("fields", []):
            teile.append(f"[{feld['name']}]\n{feld['value']}")
        if embed.get("footer"):
            teile.append(f"-- {embed['footer']['text']}")
    return "\n".join(t for t in teile if t)
