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
        "🏆 CoH2-Sonntagsladder · Gesamtwertung", "⚔️ Achse oder Alliierte · Siege : Niederlagen", "📜 Letzte Spiele",
    ]
    gesamt = embeds["🏆 CoH2-Sonntagsladder · Gesamtwertung"]
    assert gesamt["description"] == "## 🟦  7 : 3  🟧"
    assert gesamt["color"] == ausgabe.TEAM_FARBE[0], "Randfarbe = wer fuehrt"
    felder = _felder(gesamt)
    assert felder["🟦 Ace & Dipl.Agronom"].startswith("**7** Siege · 70 %")
    assert felder["🟧 Bella & UBack"].startswith("**3** Siege · 30 %")
    assert felder["Verlauf · letzte 10, neuestes rechts"] == "🟦🟦🟧🟦🟦🟧🟦🟦🟧🟦"
    assert "10 Spiele seit" in embeds["📜 Letzte Spiele"]["footer"]["text"]
    assert "/ladder" in embeds["📜 Letzte Spiele"]["footer"]["text"]
    # Nur Teams, keine Einzelspieler-Tabelle mehr
    assert "Spieler" not in ausgabe.als_text(nachricht)


def test_gleichstand():
    gesamt = ausgabe.ranglisten_nachricht(_spiele(4, sieger_ab=2), JETZT)["embeds"][0]
    assert gesamt["description"] == "## 🟦  2 : 2  🟧"
    assert gesamt["color"] == ausgabe.FARBE_NEUTRAL


def test_achse_und_alliierte_je_team_und_seite():
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
    assert duell.seiten == {"Achse": [3, 4], "Alliierte": [1, 4]}, "Achse-Duell zaehlt nicht mit"

    embed = _embeds(ausgabe.ranglisten_nachricht(spiele, JETZT))["⚔️ Achse oder Alliierte · Siege : Niederlagen"]
    assert "description" not in embed
    felder = _felder(embed)
    assert list(felder) == ["🟦 Ace & Dipl.Agronom", "🟧 Bella & UBack", "Welche Seite gewinnt?"]
    # Siege : Niederlagen je Team und Seite
    assert felder["🟦 Ace & Dipl.Agronom"] == "Achse: **2 : 2** · 50 %\nAlliierte: **0 : 1** · 0 %"
    assert felder["🟧 Bella & UBack"] == "Achse: **2 : 0** · 100 %\nAlliierte: **1 : 2** · 33 %"
    # Ohne Farben; das Achse-Duell (Spiel 5) zaehlt hier nicht mit
    assert felder["Welche Seite gewinnt?"] == (
        "Achse **3** · Alliierte **1** Siege\n"
        "-# 4 Spiele"
    )
    assert not any(farbe in ausgabe.als_text(ausgabe.ranglisten_nachricht(spiele, JETZT)) for farbe in "🟥🟩⬜")


def test_gemischtes_team_wird_als_gemischt_gefuehrt():
    roh = [relic_spiel(1, races={UBACK: 4, BELLA: 4, ACE: 2, DIPLOM: 3})]  # OKW + USF
    [spiel] = liga.spiele_aus_antwort(antwort(*roh))
    assert liga.team_seite(spiel, TEAM_AD) == liga.GEMISCHT
    felder = _felder(ausgabe.ranglisten_nachricht([spiel], JETZT)["embeds"][1])
    assert felder["🟦 Ace & Dipl.Agronom"] == "Gemischt: **1 : 0** · 100 %"
    assert "Welche Seite gewinnt?" not in felder


def test_letzte_spiele_tabelle_mit_kurznamen_neueste_oben():
    tabelle = ausgabe.letzte_spiele_tabelle(liga.duell_auswerten(_spiele(15, sieger_ab=3)))
    zeilen = tabelle.strip("`\n").splitlines()

    assert zeilen[0].split() == ["Datum", "Sieger", "als", "Dauer", "Karte"]
    assert len(zeilen) == 1 + ausgabe.LETZTE_SPIELE
    # Spalte "Datum" kann leer sein (gleicher Tag), deshalb ab Spalte "Sieger" lesen
    sieger = zeilen[0].index("Sieger")
    assert zeilen[1][sieger:].split() == ["Bella+UBack", "Allies", "0.30", "Road", "to"]  # Spiel 15, Karte auf 7 Zeichen
    assert zeilen[2][sieger:].split()[:2] == ["Ace+Dipl.Agronom", "Axis"]


def test_letzte_spiele_datum_nur_beim_obersten_spiel_des_tages():
    tag = 86_400
    sonntag = 1_793_570_400  # So 01.11.2026, 22:00 Berlin
    roh = [
        relic_spiel(1, ende=sonntag - 7 * tag),
        relic_spiel(2, ende=sonntag - 2 * 3600),
        relic_spiel(3, ende=sonntag - 3600),
        relic_spiel(4, ende=sonntag),
    ]
    tabelle = ausgabe.letzte_spiele_tabelle(liga.duell_auswerten(liga.spiele_aus_antwort(antwort(*roh))))
    datum = [zeile[:6] for zeile in tabelle.strip("`\n").splitlines()[1:]]
    assert datum == ["01.11.", "      ", "      ", "25.10."]


def test_dauer_in_stunden_punkt_minuten():
    assert [ausgabe.dauer(m) for m in (0, 7, 40, 60, 75, 125)] == [
        "0.00", "0.07", "0.40", "1.00", "1.15", "2.05",
    ]


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
    assert "🟦 **Ace & Dipl.Agronom** (Achse) schlagen 🟧 Bella & UBack (Alliierte)" in beschreibung
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
    assert r"**\*Ace\_\* & Dipl.Agronom**" in embed["description"]


def test_spiele_aufruf_zeigt_aeltere_spiele_ohne_zu_schreiben(tmp_path, monkeypatch, capsys):
    from sonntagsladder.__main__ import main
    from sonntagsladder.speicher import Speicher, Zustand

    spiele = _spiele(20, sieger_ab=3)
    speicher = Speicher(tmp_path)
    speicher.speichern(Zustand(spiele={s.id: s for s in spiele}))
    vorher = speicher.datei.read_bytes()
    monkeypatch.setenv("COH2_DATEN", str(tmp_path))

    assert main(["--spiele", "15"]) == 0
    zeilen = capsys.readouterr().out.splitlines()
    assert zeilen[0] == "15 von 20 Spielen, neueste zuerst"
    assert len(zeilen) == 2 + 15 and "```" not in zeilen

    assert main(["--spiele", "0"]) == 0
    assert capsys.readouterr().out.startswith("20 von 20 Spielen")
    assert speicher.datei.read_bytes() == vorher, "nur lesend"


def test_fusszeile_nennt_die_code_version(tmp_path, monkeypatch):
    from sonntagsladder import version

    datei = tmp_path / "version.txt"
    monkeypatch.setattr(version, "DATEI", datei)
    assert version.code_version(datei) == "code v.dev", "lokal ohne Deploy"

    datei.write_text("11 22.11.2026\n", encoding="utf-8")
    monkeypatch.setattr(version.code_version, "__defaults__", (datei,))
    fuss = ausgabe.ranglisten_nachricht(_spiele(3), JETZT)["embeds"][-1]["footer"]["text"]
    assert fuss.endswith("\ncode v.11, 22.11.2026")
