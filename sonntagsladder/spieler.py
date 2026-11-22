"""Die vier Spieler der Ladder und die CoH2-Fraktionen.

Die Schluessel sind Relic-Profil-IDs (nicht Steam-IDs). Ermitteln laesst sich
eine Profil-ID aus der Steam-ID ueber
https://coh2-api.reliclink.com/community/leaderboard/GetPersonalStat?title=coh2&profile_names=["/steam/<steam-id>"]
Der Name hier ist der Anzeigename in Discord, nicht der aktuelle Ingame-Name.
"""

SPIELER: dict[int, str] = {
    742626: "UBack",          # Steam 76561197994783260
    639680: "Bella",          # Steam 76561197994697347
    3867666: "Ace",           # Steam 76561198984634287
    111615: "Dipl.Agronom",   # Steam 76561197979850254
}

# Kurz fuer die Tabelle der letzten Spiele; wer fehlt, heisst dort wie oben.
KURZNAMEN: dict[int, str] = {}

# Die beiden festen Teams, die seit Jahren sonntags gegeneinander spielen.
# Angezeigt wird nur das Duell dieser beiden; Spiele in anderer Besetzung
# bleiben gespeichert, erscheinen aber nicht. Reihenfolge = Anzeige.
TEAMS: tuple[tuple[int, ...], ...] = (
    (3867666, 111615),  # Ace + Dipl.Agronom
    (639680, 742626),   # Bella + UBack
)
TEAM_EMOJI = ("🟦", "🟧")
TEAM_FARBE = (0x3B82F6, 0xF97316)  # Embed-Randfarbe passend zum Emoji

# race_id aus Relics matchhistoryreportresults (wie coh2stats: Achse = 0, 2)
FRAKTIONEN: dict[int, str] = {
    0: "Wehrmacht",
    1: "Sowjets",
    2: "OKW",
    3: "USF",
    4: "Briten",
}


ACHSE = frozenset({0, 2})  # Wehrmacht, OKW
ALLIIERTE = frozenset({1, 3, 4})  # Sowjets, USF, Briten


def name(profil_id: int) -> str:
    return SPIELER.get(profil_id, f"#{profil_id}")


def fraktion(race_id: int) -> str:
    return FRAKTIONEN.get(race_id, f"Fraktion {race_id}")


def kurzname(profil_id: int) -> str:
    return KURZNAMEN.get(profil_id, name(profil_id))


def seite(race_id: int | None) -> str | None:
    """'Achse', 'Alliierte' oder None (unbekannte Fraktion)."""
    if race_id in ACHSE:
        return "Achse"
    if race_id in ALLIIERTE:
        return "Alliierte"
    return None
