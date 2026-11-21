import json

import pytest

from sonntagsladder import webhook
from sonntagsladder.lauf import AbrufFehler, lauf
from sonntagsladder.speicher import Speicher
from tests.daten import ACE, BELLA, TEAM_UB, UBACK, FakeDiscord, FakeRelic, relic_spiel

URL = "https://discord.com/api/webhooks/1/token"


@pytest.fixture
def speicher(tmp_path):
    return Speicher(tmp_path / "daten")


def _lauf(speicher, relic, discord=None, url=URL):
    discord = discord or FakeDiscord()
    return lauf(
        speicher,
        webhook_url=url if discord is not None else None,
        hole=relic,
        senden=discord.senden,
        bearbeiten=discord.bearbeiten,
        jetzt=lambda: 1_800_000_000,
    )


def test_erstlauf_ohne_webhook_sammelt_nur(speicher):
    relic = FakeRelic([relic_spiel(1), relic_spiel(2)])

    ergebnis = lauf(speicher, webhook_url=None, hole=relic)

    assert (ergebnis.neu, ergebnis.gesamt, ergebnis.rangliste) == (2, 2, "ohne Webhook")
    zustand = speicher.laden()
    assert set(zustand.spiele) == {1, 2}
    assert zustand.gemeldet == {1, 2}, "Bestand beim Erstlauf gilt als gemeldet"
    assert sorted(relic.abrufe) == sorted([742626, 639680, 3867666, 111615])


def test_erstlauf_mit_webhook_sendet_nur_die_rangliste(speicher):
    discord = FakeDiscord()
    ergebnis = _lauf(speicher, FakeRelic([relic_spiel(1), relic_spiel(2)]), discord)

    assert ergebnis.rangliste == "neu gesendet"
    assert len(discord.gesendet) == 1
    assert "CoH2-Sonntagsladder" in discord.gesendet[0]
    assert speicher.laden().ranglisten_nachricht == "1001"


def test_neues_spiel_wird_gemeldet_und_rangliste_bearbeitet(speicher):
    discord = FakeDiscord()
    relic = FakeRelic([relic_spiel(1)])
    _lauf(speicher, relic, discord)

    relic.spiele.append(relic_spiel(2, sieger=TEAM_UB, verlierer=(ACE, 111615)))
    ergebnis = _lauf(speicher, relic, discord)

    assert (ergebnis.neu, ergebnis.gemeldet, ergebnis.rangliste) == (1, 1, "aktualisiert")
    assert len(discord.gesendet) == 2
    assert discord.gesendet[1].startswith("⚔️ **Neues Spiel**")
    assert discord.bearbeitet == ["1001"]

    # Nichts Neues: keine weitere Meldung, nur die Rangliste wird aufgefrischt
    ergebnis = _lauf(speicher, relic, discord)
    assert (ergebnis.neu, ergebnis.gemeldet) == (0, 0)
    assert len(discord.gesendet) == 2
    assert discord.bearbeitet == ["1001", "1001"]


def test_ein_spiel_aus_vier_historien_zaehlt_einmal(speicher):
    # FakeRelic liefert dasselbe Spiel fuer alle vier Profile
    ergebnis = lauf(speicher, webhook_url=None, hole=FakeRelic([relic_spiel(1)]))
    assert ergebnis.gesamt == 1


def test_discord_ausfall_verliert_keine_spiele(speicher):
    discord = FakeDiscord()
    relic = FakeRelic([relic_spiel(1)])
    _lauf(speicher, relic, discord)

    relic.spiele.append(relic_spiel(2))
    discord.senden_fehler = webhook.WebhookFehler("HTTP 500")
    with pytest.raises(webhook.WebhookFehler):
        _lauf(speicher, relic, discord)

    zustand = speicher.laden()
    assert 2 in zustand.spiele, "Spiel ist gespeichert, obwohl Discord streikt"
    assert 2 not in zustand.gemeldet

    # Relic hat das Spiel inzwischen vergessen, die Meldung kommt trotzdem
    relic.spiele.clear()
    discord.senden_fehler = None
    ergebnis = _lauf(speicher, relic, discord)
    assert ergebnis.gemeldet == 1
    assert "Neues Spiel" in discord.gesendet[-1]


def test_geloeschte_ranglisten_nachricht_wird_neu_gesendet(speicher):
    discord = FakeDiscord()
    relic = FakeRelic([relic_spiel(1)])
    _lauf(speicher, relic, discord)
    discord.nachrichten.clear()  # in Discord geloescht

    ergebnis = _lauf(speicher, relic, discord)

    assert ergebnis.rangliste == "neu gesendet"
    assert speicher.laden().ranglisten_nachricht == "1002"


def test_ein_spieler_nicht_abrufbar_ist_kein_problem(speicher):
    relic = FakeRelic([relic_spiel(1)])
    relic.fehler[BELLA] = TimeoutError("zu langsam")

    assert lauf(speicher, webhook_url=None, hole=relic).gesamt == 1


def test_relic_komplett_weg_bricht_ab_ohne_zustand_zu_aendern(speicher):
    lauf(speicher, webhook_url=None, hole=FakeRelic([relic_spiel(1)]))
    vorher = speicher.datei.read_text(encoding="utf-8")

    relic = FakeRelic()
    relic.fehler = {pid: OSError("kein Netz") for pid in (UBACK, BELLA, ACE, 111615)}
    with pytest.raises(AbrufFehler):
        lauf(speicher, webhook_url=None, hole=relic)

    assert speicher.datei.read_text(encoding="utf-8") == vorher


def test_zustand_ist_lesbares_json(speicher):
    lauf(speicher, webhook_url=None, hole=FakeRelic([relic_spiel(1)]))

    daten = json.loads(speicher.datei.read_text(encoding="utf-8"))
    assert daten["version"] == 1
    assert daten["spiele"][0]["id"] == 1
    assert list(speicher.ordner.glob(".zustand-*")) == [], "keine Reste vom atomaren Schreiben"
