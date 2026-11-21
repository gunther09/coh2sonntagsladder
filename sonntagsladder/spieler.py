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
    111615: "DiplomAgronom",  # Steam 76561197979850254
}

# race_id aus Relics matchhistoryreportresults (wie coh2stats: Achse = 0, 2)
FRAKTIONEN: dict[int, str] = {
    0: "Wehrmacht",
    1: "Sowjets",
    2: "OKW",
    3: "USF",
    4: "Briten",
}


def name(profil_id: int) -> str:
    return SPIELER.get(profil_id, f"#{profil_id}")


def fraktion(race_id: int) -> str:
    return FRAKTIONEN.get(race_id, f"Fraktion {race_id}")
