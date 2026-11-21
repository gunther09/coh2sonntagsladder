import io
import json
import urllib.error
import urllib.request

import pytest

from sonntagsladder import webhook

URL = "https://discord.com/api/webhooks/123456789/geheim-TOKEN_xyz"


class FakeAntwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_fehler(code, koerper=b""):
    return urllib.error.HTTPError("https://example.invalid", code, "x", {}, io.BytesIO(koerper))


@pytest.fixture
def netz(monkeypatch):
    """Ersetzt urlopen durch eine Liste vorbereiteter Antworten."""
    anfragen = []
    antworten = []

    def urlopen(anfrage, timeout=None):
        anfragen.append(anfrage)
        ergebnis = antworten.pop(0)
        if isinstance(ergebnis, Exception):
            raise ergebnis
        return FakeAntwort(json.dumps(ergebnis).encode() if ergebnis is not None else b"")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(webhook.time, "sleep", lambda _s: None)
    return anfragen, antworten


def test_url_pruefung():
    assert webhook.pruefe_url(f" {URL} ") == URL
    assert webhook.pruefe_url("https://discordapp.com/api/webhooks/1/abc?thread_id=5")
    for falsch in ("", "http://discord.com/api/webhooks/1/abc", "https://evil.example/api/webhooks/1/abc"):
        with pytest.raises(webhook.WebhookFehler) as fehler:
            webhook.pruefe_url(falsch)
        assert "TOKEN" not in str(fehler.value)


def test_senden_wartet_auf_id_und_unterdrueckt_erwaehnungen(netz):
    anfragen, antworten = netz
    antworten.append({"id": "42"})

    assert webhook.senden(URL, "@everyone hallo") == "42"
    anfrage = anfragen[0]
    assert anfrage.get_method() == "POST"
    assert anfrage.full_url == URL + "?wait=true"
    assert json.loads(anfrage.data)["allowed_mentions"] == {"parse": []}


def test_bearbeiten_mit_thread_parameter(netz):
    anfragen, antworten = netz
    antworten.append({"id": "42"})

    webhook.bearbeiten(URL + "?thread_id=7", "42", "neu")

    assert anfragen[0].get_method() == "PATCH"
    assert anfragen[0].full_url == URL + "/messages/42?thread_id=7"


def test_geloeschte_nachricht(netz):
    _anfragen, antworten = netz
    antworten.append(_http_fehler(404))

    with pytest.raises(webhook.NachrichtFehlt):
        webhook.bearbeiten(URL, "42", "neu")


def test_geloeschter_webhook_beim_senden_nennt_kein_token(netz):
    _anfragen, antworten = netz
    antworten.append(_http_fehler(404))

    with pytest.raises(webhook.WebhookFehler) as fehler:
        webhook.senden(URL, "x")
    assert not isinstance(fehler.value, webhook.NachrichtFehlt)
    assert "TOKEN" not in str(fehler.value) and "123456789" not in str(fehler.value)


def test_drosselung_wird_abgewartet(netz):
    anfragen, antworten = netz
    antworten.extend([_http_fehler(429, b'{"retry_after": 0.2}'), {"id": "43"}])

    assert webhook.senden(URL, "x") == "43"
    assert len(anfragen) == 2
