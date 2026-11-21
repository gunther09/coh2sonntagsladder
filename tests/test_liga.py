from sonntagsladder import liga
from tests.daten import (
    ACE, BELLA, DIPLOM, FREMDER, TEAM_AD, TEAM_UB, UBACK, antwort, relic_spiel,
)


def test_liest_custom_game_der_vier():
    [spiel] = liga.spiele_aus_antwort(antwort(relic_spiel(1, dauer_min=36)))

    assert spiel.id == 1
    assert spiel.sieger == (ACE, DIPLOM)
    assert spiel.verlierer == (UBACK, BELLA)
    assert spiel.dauer_minuten == 36
    assert spiel.race_id(ACE) == 2 and spiel.race_id(UBACK) == 4


def test_ignoriert_alles_ausser_ladder_spielen():
    spiele = liga.spiele_aus_antwort(antwort(
        relic_spiel(1, matchtype=2),                                     # Automatch 2v2
        relic_spiel(2, sieger=(UBACK, FREMDER), verlierer=TEAM_AD),      # Fremder statt Bella
        relic_spiel(3, resulttypes={ACE: 0, DIPLOM: 0}),                 # abgebrochen, kein Sieger
        relic_spiel(4, resulttypes={ACE: 0}),                            # Team uneinig
        relic_spiel(5),                                                  # gueltig
    ))

    assert [s.id for s in spiele] == [5]


def test_ignoriert_spiele_mit_mehr_als_vier_spielern():
    spiel = relic_spiel(1)
    spiel["matchhistoryreportresults"].append(dict(spiel["matchhistoryreportresults"][0], profile_id=FREMDER))

    assert liga.spiele_aus_antwort(antwort(spiel)) == []


def test_ignoriert_kaputte_eintraege_statt_abzubrechen():
    kaputt = relic_spiel(1)
    del kaputt["completiontime"]

    assert [s.id for s in liga.spiele_aus_antwort(antwort(kaputt, relic_spiel(2)))] == [2]


def test_spiel_ueberlebt_speichern_und_laden():
    [spiel] = liga.spiele_aus_antwort(antwort(relic_spiel(7)))

    assert liga.Spiel.aus_dict(spiel.als_dict()) == spiel


def _spiele(*sieger_teams):
    roh = [
        relic_spiel(i, sieger=team, verlierer=TEAM_UB if team == TEAM_AD else TEAM_AD)
        for i, team in enumerate(sieger_teams, start=1)
    ]
    return liga.spiele_aus_antwort(antwort(*roh))


def test_spielerrangliste_mit_geteilten_plaetzen_und_serie():
    spiele = _spiele(TEAM_AD, TEAM_UB, TEAM_AD, TEAM_AD, TEAM_UB, TEAM_UB, TEAM_AD)

    rangliste = liga.spielerrangliste(spiele)

    assert [(platz, spieler) for platz, spieler, _ in rangliste] == [
        (1, ACE), (1, DIPLOM), (3, UBACK), (3, BELLA),
    ]
    _, _, ace = rangliste[0]
    assert (ace.spiele, ace.siege, ace.niederlagen) == (7, 4, 3)
    assert ace.serie == (True, 1)
    _, _, uback = rangliste[2]
    assert uback.serie == (False, 1)


def test_serie_zaehlt_gleiche_ergebnisse_am_ende():
    bilanz = liga.Bilanz([True, False, False, False])
    assert bilanz.serie == (False, 3)
    assert liga.Bilanz().serie is None


def test_spieler_ohne_spiele_stehen_hinten():
    rangliste = liga.spielerrangliste([])
    assert {platz for platz, _, _ in rangliste} == {1}
    assert all(b.quote is None for _, _, b in rangliste)


def test_teams_und_direkter_vergleich():
    spiele = _spiele(TEAM_AD, TEAM_AD, TEAM_UB)

    [(platz_a, team_a, bilanz_a), (platz_b, team_b, bilanz_b)] = liga.teamrangliste(spiele)
    assert (platz_a, team_a, bilanz_a.siege, bilanz_a.niederlagen) == (1, TEAM_AD, 2, 1)
    assert (platz_b, team_b, bilanz_b.siege, bilanz_b.niederlagen) == (2, TEAM_UB, 1, 2)
    assert liga.duell(spiele, TEAM_AD, TEAM_UB) == (2, 1)
    assert liga.duell(spiele, (BELLA, UBACK), (DIPLOM, ACE)) == (1, 2)  # Reihenfolge egal


def test_wechselnde_teams_werden_getrennt_gefuehrt():
    roh = [
        relic_spiel(1, sieger=TEAM_AD, verlierer=TEAM_UB),
        relic_spiel(2, sieger=(UBACK, ACE), verlierer=(BELLA, DIPLOM)),
    ]
    spiele = liga.spiele_aus_antwort(antwort(*roh))

    teams = {team: (b.siege, b.niederlagen) for _, team, b in liga.teamrangliste(spiele)}
    assert teams == {TEAM_AD: (1, 0), (UBACK, ACE): (1, 0), TEAM_UB: (0, 1), (BELLA, DIPLOM): (0, 1)}
    spieler = {p: (b.siege, b.niederlagen) for _, p, b in liga.spielerrangliste(spiele)}
    assert spieler == {ACE: (2, 0), UBACK: (1, 1), DIPLOM: (1, 1), BELLA: (0, 2)}


def test_kartennamen():
    assert liga.kartenname("4p_road_to_kharkov") == "Road to Kharkov"
    assert liga.kartenname("4 duclair") == "Duclair"
    assert liga.kartenname("highwaybaku") == "Highwaybaku"
    assert liga.kartenname("6p_across_the_rhine") == "Across the Rhine"
    assert liga.kartenname("") == "?"
