from sonntagsladder import ausgabe, liga
from tests.daten import ACE, DIPLOM, TEAM_AD, TEAM_UB, antwort, relic_spiel

JETZT = 1_800_000_000


def _spiele(anzahl, sieger_ab=None):
    roh = []
    for i in range(1, anzahl + 1):
        sieger = TEAM_AD if (sieger_ab is None or i % sieger_ab) else TEAM_UB
        roh.append(relic_spiel(i, sieger=sieger, verlierer=TEAM_UB if sieger == TEAM_AD else TEAM_AD))
    return liga.spiele_aus_antwort(antwort(*roh))


def test_rangliste_ohne_spiele():
    text = ausgabe.ranglisten_text([], JETZT)
    assert "Noch keine Spiele" in text
    assert len(text) <= ausgabe.DISCORD_LIMIT


def test_rangliste_mit_tabellen_und_letzten_spielen():
    text = ausgabe.ranglisten_text(_spiele(10, sieger_ab=3), JETZT)

    assert "**Spieler**" in text and "**Teams**" in text and "**Letzte Spiele**" in text
    assert "Ace + DiplomAgronom" in text
    assert text.count("schlagen") == ausgabe.LETZTE_SPIELE
    assert "10 Spiele seit" in text
    assert len(text) <= ausgabe.DISCORD_LIMIT


def test_rangliste_bleibt_unter_dem_discord_limit_auch_bei_vielen_spielen():
    assert len(ausgabe.ranglisten_text(_spiele(500, sieger_ab=2), JETZT)) <= ausgabe.DISCORD_LIMIT


def test_meldung_neues_spiel_mit_fraktionen_und_duellstand():
    spiele = _spiele(10, sieger_ab=3)  # Spiele 3, 6, 9 gewinnt UBack + Bella

    text = ausgabe.neue_spiele_text(spiele[-1:], spiele)

    assert text.startswith("⚔️ **Neues Spiel**")
    assert "**Ace** (OKW) + **DiplomAgronom** (Wehrmacht) schlagen UBack (Briten) + Bella (Briten)" in text
    assert "Road to Kharkov" in text and "30 min" in text
    assert "Stand im Duell: **Ace + DiplomAgronom** 7 : 3 UBack + Bella" in text


def test_meldung_mehrerer_spiele_wird_gekappt():
    spiele = _spiele(15)
    text = ausgabe.neue_spiele_text(spiele, spiele)

    assert text.startswith("⚔️ **15 neue Spiele**")
    assert text.count("schlagen") == ausgabe.NEUE_SPIELE_MAX
    assert "… und 5 weitere" in text
    assert text.count("Stand im Duell") == 1


def test_markdown_in_namen_wird_entschaerft(monkeypatch):
    from sonntagsladder import spieler

    monkeypatch.setitem(spieler.SPIELER, ACE, "*Ace_*")
    spiele = _spiele(1)
    text = ausgabe.neue_spiele_text(spiele, spiele)
    assert r"**\*Ace\_\***" in text


def test_spielertabelle_ist_ausgerichtet():
    tabelle = ausgabe.spielertabelle(_spiele(4, sieger_ab=2))
    zeilen = tabelle.strip("`\n").splitlines()
    assert zeilen[0].split() == ["Pl", "Spieler", "Sp", "S", "N", "Quote", "Serie"]
    # alle gleichauf: gleicher Platz, Reihenfolge wie in spieler.py
    assert [z.split()[1] for z in zeilen[1:]] == ["UBack", "Bella", "Ace", "DiplomAgronom"]
    assert zeilen[3].split() == ["1.", "Ace", "4", "2", "2", "50%", "1N"]
    # rechtsbuendige Zahlenspalte: Ende von "Sp" im Kopf == Ende der Zahl darunter
    ende_sp = zeilen[0].index(" Sp ") + 2
    assert zeilen[1][ende_sp] == "4" and zeilen[1][ende_sp - 1] == " "
