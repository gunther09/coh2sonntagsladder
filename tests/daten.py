"""Testdaten im Format der Relic-Antwort (getRecentMatchHistoryByProfileId)."""

from __future__ import annotations

UBACK, BELLA, ACE, DIPLOM = 742626, 639680, 3867666, 111615
FREMDER = 999001

TEAM_UB = (UBACK, BELLA)
TEAM_AD = (ACE, DIPLOM)

BASIS_ZEIT = 1_792_000_000  # Mitte Oktober 2026


def relic_spiel(
    spiel_id: int,
    *,
    sieger=TEAM_AD,
    verlierer=TEAM_UB,
    ende: int | None = None,
    dauer_min: int = 30,
    matchtype: int = 0,
    karte: str = "4p_road_to_kharkov",
    races: dict[int, int] | None = None,
    resulttypes: dict[int, int] | None = None,
) -> dict:
    ende = BASIS_ZEIT + spiel_id * 3600 if ende is None else ende
    races = races or {UBACK: 4, BELLA: 4, ACE: 2, DIPLOM: 0}
    berichte = []
    for team_id, (team, ergebnis) in enumerate(((sieger, 1), (verlierer, 0))):
        for profil_id in team:
            berichte.append({
                "matchhistory_id": spiel_id,
                "profile_id": profil_id,
                "resulttype": (resulttypes or {}).get(profil_id, ergebnis),
                "teamid": team_id,
                "race_id": races.get(profil_id, 1),
                "xpgained": 0,
                "counters": "{}",
                "matchstartdate": ende - dauer_min * 60,
            })
    return {
        "id": spiel_id,
        "creator_profile_id": sieger[0],
        "mapname": karte,
        "maxplayers": 4,
        "matchtype_id": matchtype,
        "description": "SESSION_MATCH_KEY" if matchtype == 0 else "AUTOMATCH",
        "startgametime": ende - dauer_min * 60,
        "completiontime": ende,
        "matchhistoryreportresults": berichte,
    }


def antwort(*spiele: dict) -> dict:
    return {"result": {"code": 0, "message": "SUCCESS"}, "matchHistoryStats": list(spiele), "profiles": []}


class FakeRelic:
    """Liefert je Profil-ID eine vorbereitete Antwort; zaehlt die Abrufe."""

    def __init__(self, spiele: list[dict] | None = None):
        self.spiele = list(spiele or [])
        self.fehler: dict[int, Exception] = {}
        self.abrufe: list[int] = []

    def __call__(self, profil_id: int) -> dict:
        self.abrufe.append(profil_id)
        if profil_id in self.fehler:
            raise self.fehler[profil_id]
        eigene = [
            s for s in self.spiele
            if profil_id in {b["profile_id"] for b in s["matchhistoryreportresults"]}
        ]
        return antwort(*eigene)


class FakeDiscord:
    """Webhook-Ersatz: merkt sich gesendete und bearbeitete Nachrichten."""

    def __init__(self):
        self.nachrichten: dict[str, str] = {}
        self.gesendet: list[str] = []
        self.bearbeitet: list[str] = []
        self.naechste_id = 1000
        self.senden_fehler: Exception | None = None

    def senden(self, url: str, text: str) -> str:
        if self.senden_fehler is not None:
            raise self.senden_fehler
        assert len(text) <= 2000, "Discord nimmt hoechstens 2000 Zeichen"
        self.naechste_id += 1
        nachricht_id = str(self.naechste_id)
        self.nachrichten[nachricht_id] = text
        self.gesendet.append(text)
        return nachricht_id

    def bearbeiten(self, url: str, nachricht_id: str, text: str) -> None:
        from sonntagsladder.webhook import NachrichtFehlt

        if nachricht_id not in self.nachrichten:
            raise NachrichtFehlt("weg")
        assert len(text) <= 2000
        self.nachrichten[nachricht_id] = text
        self.bearbeitet.append(nachricht_id)
