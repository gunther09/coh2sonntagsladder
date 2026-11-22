from sonntagsladder import ausgabe, liga
from tests.daten import (
    ACE, BELLA, DIPLOM, TEAM_AD, TEAM_UB, UBACK, antwort, pruefe_discord_grenzen, relic_spiel,
)

JETZT = 1_800_000_000
ACHSE_AD = {UBACK: 4, BELLA: 4, ACE: 2, DIPLOM: 0}  # Ace + Diplom Achse, Bella + UBack Briten
ACHSE_UB = {UBACK: 2, BELLA: 0, ACE: 3, DIPLOM: 1}


def _spiele(anzahl, sieger_ab=None):
    roh = []
    for i in range(1, anzahl + 1):
        sieger = TEAM_AD if (sieger_ab is None or i % sieger_ab) else TEAM_UB
        roh.append(relic_spiel(i, sieger=sieger, verlierer=TEAM_UB if sieger == TEAM_AD else TEAM_AD))
    return liga.spiele_aus_antwort(antwort(*roh))


def _embeds(nachricht):
    pruefe_discord_grenzen(nachricht)
    return {embed["title"]: embed for embed in nachricht["embeds"]}


def _felder(embed):
    return {feld["name"]: feld["value"] for feld in embed.get("fields", [])}


def test_rangliste_ohne_spiele():
    nachricht = ausgabe.ranglisten_nachricht([], JETZT)
    [embed] = nachricht["embeds"]
    assert "Noch keine Spiele" in embed["description"]
    assert "/ladder" in embed["footer"]["text"]


def test_rangliste_gesamtwertung_oben_dann_seiten_dann_letzte_spiele():
    nachricht = ausgabe.ranglisten_nachricht(_spiele(10, sieger_ab=3), JETZT)
    embeds = _embeds(nachricht)

    assert list(embeds) == [
        "🏆 CoH2-Sonntagsladder · Gesamtwertung", "⚔️ Achse oder Alliierte", "📜 Letzte Spiele",
    ]
    gesamt = embeds["🏆 CoH2-Sonntagsladder · Gesamtwertung"]
    assert gesamt["description"].startswith("## 🟦  7 : 3  🟧")
    assert "**Ace & DiplomAgronom** führen mit 4 Siegen Vorsprung" in gesamt["description"]
    felder = _felder(gesamt)
    assert felder["🟦 Ace & DiplomAgronom"].startswith("**7** Siege · 70 %")
    assert felder["🟧 Bella & UBack"].startswith("**3** Siege · 30 %")
    assert felder["Verlauf · letzte 10, neuestes rechts"] == "🟦🟦🟧🟦🟦🟧🟦🟦🟧🟦"
    assert "10 Spiele seit" in embeds["📜 Letzte Spiele"]["footer"]["text"]
    assert "/ladder" in embeds["📜 Letzte Spiele"]["footer"]["text"]
    # Nur Teams, keine Einzelspieler-Tabelle mehr
    assert "Spieler" not in ausgabe.als_text(nachricht)


def test_gleichstand():
    gesamt = ausgabe.ranglisten_nachricht(_spiele(4, sieger_ab=2), JETZT)["embeds"][0]
    assert gesamt["description"] == "## 🟦  2 : 2  🟧\nGleichstand."
    assert gesamt["color"] == ausgabe.FARBE_NEUTRAL


def test_achse_und_alliierte_je_team_und_paarung():
    roh = [
        relic_spiel(1, sieger=TEAM_AD, verlierer=TEAM_UB, races=ACHSE_AD),
        relic_spiel(2, sieger=TEAM_AD, verlierer=TEAM_UB, races=ACHSE_AD),
        relic_spiel(3, sieger=TEAM_UB, verlierer=TEAM_AD, races=ACHSE_AD),
        relic_spiel(4, sieger=TEAM_UB, verlierer=TEAM_AD, races=ACHSE_UB),
        # Achse-Duell: beide Teams Achse
        relic_spiel(5, sieger=TEAM_UB, verlierer=TEAM_AD, races={UBACK: 0, BELLA: 2, ACE: 0, DIPLOM: 2}),
    ]
    spiele = liga.spiele_aus_antwort(antwort(*roh))

    duell = liga.duell_auswerten(spiele)
    ad, ub = duell.nach_seite
    assert (ad["Achse"].siege, ad["Achse"].spiele) == (2, 4)
    assert (ad["Alliierte"].siege, ad["Alliierte"].spiele) == (0, 1)
    assert (ub["Achse"].siege, ub["Achse"].spiele) == (2, 2)
    assert (ub["Alliierte"].siege, ub["Alliierte"].spiele) == (1, 3)
    assert duell.paarungen == {
        ("Achse", "Alliierte"): [2, 1],
        ("Alliierte", "Achse"): [0, 1],
        ("Achse", "Achse"): [0, 1],
    }
    assert duell.seiten == {"Achse": [3, 4], "Alliierte": [1, 4]}, "Achse-Duell zaehlt nicht mit"

    felder = _felder(_embeds(ausgabe.ranglisten_nachricht(spiele, JETZT))["⚔️ Achse oder Alliierte"])
    # Rangliste je Seite: bessere Quote zuerst
    assert felder["Mit Achse"] == "🟧 **2** von 2 · 100 %\n🟦 **2** von 4 · 50 %"
    assert felder["Mit Alliierten"] == "🟧 **1** von 3 · 33 %\n🟦 **0** von 1 · 0 %"
    assert felder["Paarungen"].splitlines() == [
        "🟦 Achse gegen 🟧 Alliierte: **2 : 1**",
        "🟦 Alliierte gegen 🟧 Achse: **0 : 1**",
        "🟦 Achse gegen 🟧 Achse: **0 : 1**",
    ]
    assert felder["Welche Seite gewinnt?"].startswith("Achse 3 · Alliierte 1 (von 4 Spielen")


def test_gemischtes_team_wird_als_gemischt_gefuehrt():
    roh = [relic_spiel(1, races={UBACK: 4, BELLA: 4, ACE: 2, DIPLOM: 3})]  # OKW + USF
    [spiel] = liga.spiele_aus_antwort(antwort(*roh))
    assert liga.team_seite(spiel, TEAM_AD) == liga.GEMISCHT
    felder = _felder(ausgabe.ranglisten_nachricht([spiel], JETZT)["embeds"][1])
    assert "Gemischt" in felder and "Welche Seite gewinnt?" not in felder


def test_letzte_spiele_tabelle_mit_kurznamen_neueste_oben():
    tabelle = ausgabe.letzte_spiele_tabelle(liga.duell_auswerten(_spiele(12, sieger_ab=3)))
    zeilen = tabelle.strip("`\n").splitlines()

    assert zeilen[0].split() == ["Datum", "Sieger", "als", "Karte"]
    assert len(zeilen) == 1 + ausgabe.LETZTE_SPIELE
    assert zeilen[1].split()[1:] == ["Bella+UBack", "Alliierte", "Road", "to", "Kharkov"]  # Spiel 12
    assert zeilen[2].split()[1:3] == ["Ace+Diplom", "Achse"]
    assert "DiplomAgronom" not in tabelle


def test_andere_besetzungen_erscheinen_nicht():
    roh = [
        relic_spiel(1, sieger=TEAM_AD, verlierer=TEAM_UB),
        relic_spiel(2, sieger=(UBACK, ACE), verlierer=(BELLA, DIPLOM)),
    ]
    spiele = liga.spiele_aus_antwort(antwort(*roh))

    assert [s.id for s in liga.teamduelle(spiele)] == [1]
    assert ausgabe.neue_spiele_nachricht(spiele[1:], spiele) is None
    text = ausgabe.als_text(ausgabe.ranglisten_nachricht(spiele, JETZT))
    assert "1 : 0" in text and "1 Spiele seit" in text


def test_rangliste_bleibt_unter_den_discord_grenzen_auch_bei_vielen_spielen():
    _embeds(ausgabe.ranglisten_nachricht(_spiele(500, sieger_ab=2), JETZT))


def test_meldung_neues_spiel_mit_seiten_und_gesamtstand():
    spiele = _spiele(10, sieger_ab=3)  # Spiele 3, 6, 9 gewinnen Bella + UBack

    [embed] = ausgabe.neue_spiele_nachricht(spiele[-1:], spiele)["embeds"]

    assert embed["title"] == "⚔️ Neues Spiel"
    beschreibung = embed["description"]
    assert "🟦 **Ace & DiplomAgronom** (Achse) schlagen 🟧 Bella & UBack (Alliierte)" in beschreibung
    assert "Road to Kharkov" in beschreibung and "30 min" in beschreibung
    assert beschreibung.endswith("Gesamtstand: 🟦 **7 : 3** 🟧")
    assert embed["color"] == ausgabe.TEAM_FARBE[0]


def test_meldung_mehrerer_spiele_wird_gekappt():
    spiele = _spiele(15)
    nachricht = ausgabe.neue_spiele_nachricht(spiele, spiele)
    _embeds(nachricht)
    [embed] = nachricht["embeds"]

    assert embed["title"] == "⚔️ 15 neue Spiele"
    assert embed["description"].count("schlagen") == ausgabe.NEUE_SPIELE_MAX
    assert "… und 5 weitere" in embed["description"]


def test_markdown_in_namen_wird_entschaerft(monkeypatch):
    from sonntagsladder import spieler

    monkeypatch.setitem(spieler.SPIELER, ACE, "*Ace_*")
    spiele = _spiele(1)
    [embed] = ausgabe.neue_spiele_nachricht(spiele, spiele)["embeds"]
    assert r"**\*Ace\_\* & DiplomAgronom**" in embed["description"]
