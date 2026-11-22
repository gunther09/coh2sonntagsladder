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
LETZTE_SPIELE = 12
VERLAUF_MAX = 20
NEUE_SPIELE_MAX = 10
KARTE_MAX = 7  # "Minsk Pocket Frontline" -> "Minsk P"
FARBE_NEUTRAL = 0x6B7280
# Die Befehle stellt der Elternabend-Bot im selben Server bereit (Repo DiscordBot):
# /ladder startet den Dienst dieser Ladder, /ladder_spiele ruft
# `python -m sonntagsladder --spiele N` auf und zeigt die Tabelle nur dem Aufrufer.
AKTUALISIEREN = "/ladder aktualisiert sofort · /ladder_spiele zeigt ältere Spiele"

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
    """'Ace & Dipl.Agronom' (ohne Markdown)."""
    return " & ".join(name(profil_id) for profil_id in team)


def kurzer_teamname(team: Iterable[int]) -> str:
    """'Ace+Dipl.Agronom' fuer die Tabelle."""
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


def _tabelle(kopf: list[str], zeilen: list[list[str]], *, zaun: bool = True) -> str:
    breiten = [max(len(str(z[i])) for z in [kopf, *zeilen]) for i in range(len(kopf))]

    def zeile(werte):
        return "  ".join(str(w).ljust(breiten[i]) for i, w in enumerate(werte)).rstrip()

    text = "\n".join([zeile(kopf), *(zeile(z) for z in zeilen)])
    return f"```\n{text}\n```" if zaun else text


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
        farbe = FARBE_NEUTRAL
    else:
        farbe = TEAM_FARBE[0 if a.siege > b.siege else 1]  # Randfarbe = wer fuehrt

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
        "description": f"## {TEAM_EMOJI[0]}  {a.siege} : {b.siege}  {TEAM_EMOJI[1]}",
        "color": farbe,
        "fields": felder,
    }


def dauer(minuten: int) -> str:
    """40 -> '0.40', 75 -> '1.15' (Stunden.Minuten)."""
    return f"{minuten // 60}.{minuten % 60:02d}"


def _seite(seite_name: str) -> str:
    return seite_name.capitalize()


def _seiten_embed(duell: liga.Duell) -> dict:
    felder = []
    for i in (0, 1):
        zeilen = []
        for seite_name in ("Achse", "Alliierte", liga.GEMISCHT):
            b = duell.nach_seite[i].get(seite_name)
            if b is None:
                continue
            zeilen.append(
                f"{_seite(seite_name)}: **{b.siege} : {b.niederlagen}** · "
                f"{_prozent(b.siege, b.spiele)}"
            )
        if zeilen:
            felder.append({
                "name": f"{TEAM_EMOJI[i]} {teamname(TEAMS[i])}",
                "value": "\n".join(zeilen),
                "inline": True,
            })

    achse, alliierte = duell.seiten["Achse"], duell.seiten["Alliierte"]
    if achse[1]:
        felder.append({
            "name": "Welche Seite gewinnt?",
            "value": f"Achse **{achse[0]}** · Alliierte **{alliierte[0]}** Siege\n"
                     f"-# von {achse[1]} Spielen Achse gegen Alliierte",
            "inline": False,
        })
    return {
        # Die Teamspalten zeigen Siege : Niederlagen - knapp im Titel erklaert
        "title": "⚔️ Achse oder Alliierte · Siege : Niederlagen",
        "color": FARBE_NEUTRAL,
        "fields": felder,
    }


# Kurz fuer die schmale Spalte "als" (sonst deutsch: Achse, Alliierte)
TABELLEN_SEITE = {"Achse": "Axis", "Alliierte": "Allies", liga.GEMISCHT: "Mix"}


def letzte_spiele_tabelle(duell: liga.Duell, anzahl: int | None = LETZTE_SPIELE, *, zaun: bool = True) -> str:
    """Neueste zuerst; anzahl None = alle. zaun=False ohne ```-Codeblock."""
    zeilen = []
    auswahl = duell.spiele if anzahl is None else duell.spiele[-anzahl:]
    vorheriger_tag = None
    for spiel in reversed(auswahl):
        # Spiele desselben Tages: Datum nur in der obersten Zeile, damit die
        # Spieltage als Bloecke sichtbar sind.
        tag = _zeit(spiel.ende).strftime("%d.%m.")
        zeilen.append([
            tag if tag != vorheriger_tag else "",
            kurzer_teamname(TEAMS[liga.sieger_index(spiel)]),
            TABELLEN_SEITE.get(liga.team_seite(spiel, spiel.sieger), "?"),
            dauer(spiel.dauer_minuten),
            liga.kartenname(spiel.karte)[:KARTE_MAX].rstrip(),
        ])
        vorheriger_tag = tag
    return _tabelle(["Datum", "Sieger", "als", "Dauer", "Karte"], zeilen, zaun=zaun)


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
