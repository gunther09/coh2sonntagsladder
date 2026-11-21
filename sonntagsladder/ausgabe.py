"""Texte fuer Discord: die angeheftete Ranglisten-Nachricht und die Meldung
zu neuen Spielen. Discord erlaubt hoechstens 2000 Zeichen je Nachricht."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from . import liga
from .spieler import fraktion, name

DISCORD_LIMIT = 2000
LETZTE_SPIELE = 5
NEUE_SPIELE_MAX = 10
TITEL = "🏆 **CoH2-Sonntagsladder** · 2 vs 2, Custom Games"

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
    for zeichen in ("\\", "*", "_", "~", "|", "`", ">"):
        text = text.replace(zeichen, "\\" + zeichen)
    return text


def teamname(team: Iterable[int]) -> str:
    return " + ".join(name(profil_id) for profil_id in team)


def _team_mit_fraktionen(spiel: liga.Spiel, team: tuple[int, ...], *, fett: bool) -> str:
    teile = []
    for profil_id in team:
        spielername = _markdown(name(profil_id))
        if fett:
            spielername = f"**{spielername}**"
        race_id = spiel.race_id(profil_id)
        teile.append(f"{spielername} ({fraktion(race_id)})" if race_id is not None else spielername)
    return " + ".join(teile)


def _quote(bilanz: liga.Bilanz) -> str:
    return "-" if bilanz.quote is None else f"{bilanz.quote * 100:.0f}%"


def _serie(bilanz: liga.Bilanz) -> str:
    serie = bilanz.serie
    if serie is None:
        return "-"
    sieg, laenge = serie
    return f"{laenge}{'S' if sieg else 'N'}"


def _tabelle(kopf: list[str], zeilen: list[list[str]], rechtsbuendig: set[int]) -> str:
    breiten = [max(len(str(z[i])) for z in [kopf, *zeilen]) for i in range(len(kopf))]

    def zeile(werte):
        zellen = [
            str(w).rjust(breiten[i]) if i in rechtsbuendig else str(w).ljust(breiten[i])
            for i, w in enumerate(werte)
        ]
        return "  ".join(zellen).rstrip()

    return "```\n" + "\n".join([zeile(kopf), *(zeile(z) for z in zeilen)]) + "\n```"


def spielertabelle(spiele: list[liga.Spiel]) -> str:
    zeilen = [
        [f"{platz}.", name(profil_id), b.spiele, b.siege, b.niederlagen, _quote(b), _serie(b)]
        for platz, profil_id, b in liga.spielerrangliste(spiele)
    ]
    return _tabelle(["Pl", "Spieler", "Sp", "S", "N", "Quote", "Serie"], zeilen, {0, 2, 3, 4, 5})


def teamtabelle(spiele: list[liga.Spiel]) -> str:
    zeilen = [
        [teamname(team), b.spiele, b.siege, b.niederlagen, _quote(b)]
        for _platz, team, b in liga.teamrangliste(spiele)
    ]
    return _tabelle(["Team", "Sp", "S", "N", "Quote"], zeilen, {1, 2, 3, 4})


def spielzeile(spiel: liga.Spiel) -> str:
    return (
        f"`{datum_zeit(spiel.ende)}` **{_markdown(teamname(spiel.sieger))}** schlagen "
        f"{_markdown(teamname(spiel.verlierer))} · {liga.kartenname(spiel.karte)}"
    )


def ranglisten_text(spiele: Iterable[liga.Spiel], jetzt: int) -> str:
    alle = liga.chronologisch(spiele)
    if not alle:
        return "\n".join([
            TITEL,
            "Noch keine Spiele erfasst. Sobald die vier ein Custom Game 2 vs 2 gegeneinander "
            "beendet haben, steht es hier.",
            f"-# Stand {datum_zeit(jetzt)} · Daten von Relic, geprüft alle 15 Minuten",
        ])

    fuss = (
        f"-# {len(alle)} Spiele seit {datum(alle[0].ende)} · Stand {datum_zeit(jetzt)} · "
        "Daten von Relic, geprüft alle 15 Minuten"
    )
    for anzahl_letzte in range(LETZTE_SPIELE, -1, -1):
        teile = [TITEL, "**Spieler**", spielertabelle(alle), "**Teams**", teamtabelle(alle)]
        if anzahl_letzte:
            teile.append("**Letzte Spiele**")
            teile.extend(spielzeile(s) for s in reversed(alle[-anzahl_letzte:]))
        teile.append(fuss)
        text = "\n".join(teile)
        if len(text) <= DISCORD_LIMIT:
            return text
    return text[: DISCORD_LIMIT - 1] + "…"


def neue_spiele_text(neue: Iterable[liga.Spiel], alle: Iterable[liga.Spiel]) -> str:
    neue = liga.chronologisch(neue)
    alle = list(alle)
    ueberschrift = "⚔️ **Neues Spiel**" if len(neue) == 1 else f"⚔️ **{len(neue)} neue Spiele**"
    zeilen = [ueberschrift]
    for spiel in neue[:NEUE_SPIELE_MAX]:
        zeilen.append(
            f"{_team_mit_fraktionen(spiel, spiel.sieger, fett=True)} schlagen "
            f"{_team_mit_fraktionen(spiel, spiel.verlierer, fett=False)}"
        )
        zeilen.append(
            f"-# {datum_zeit(spiel.ende)} · {liga.kartenname(spiel.karte)} · {spiel.dauer_minuten} min"
        )
    if len(neue) > NEUE_SPIELE_MAX:
        zeilen.append(f"… und {len(neue) - NEUE_SPIELE_MAX} weitere")

    # Stand im direkten Duell, je Paarung einmal (bei festen Teams genau eine Zeile)
    gesehen = set()
    for spiel in neue:
        paarung = frozenset((spiel.sieger, spiel.verlierer))
        if paarung in gesehen:
            continue
        gesehen.add(paarung)
        team_a, team_b = spiel.sieger, spiel.verlierer
        siege_a, siege_b = liga.duell(alle, team_a, team_b)
        if siege_b > siege_a:
            team_a, team_b, siege_a, siege_b = team_b, team_a, siege_b, siege_a
        zeilen.append(
            f"Stand im Duell: **{_markdown(teamname(team_a))}** {siege_a} : {siege_b} "
            f"{_markdown(teamname(team_b))}"
        )

    text = "\n".join(zeilen)
    return text if len(text) <= DISCORD_LIMIT else text[: DISCORD_LIMIT - 1] + "…"
