"""Discord-Webhook: Nachricht senden und eigene Nachricht bearbeiten.

Die Webhook-URL enthaelt das Token und ist damit ein Geheimnis. Sie darf in
keiner Meldung und keinem Log auftauchen - deshalb nennen die Fehler hier nur
den HTTP-Status, nie die URL.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "coh2-sonntagsladder/1.0 (+https://github.com/gunther09/coh2sonntagsladder)"
TIMEOUT_SEKUNDEN = 20
VERSUCHE = 3

_WEBHOOK_URL = re.compile(
    r"^https://(?:(?:ptb|canary)\.)?discord(?:app)?\.com/api(?:/v\d+)?/webhooks/\d+/[\w-]+/?(?:\?.*)?$"
)


class WebhookFehler(RuntimeError):
    pass


class NachrichtFehlt(WebhookFehler):
    """Die zu bearbeitende Nachricht gibt es nicht mehr (z.B. in Discord geloescht)."""


def pruefe_url(url: str) -> str:
    url = (url or "").strip()
    if not _WEBHOOK_URL.match(url):
        raise WebhookFehler(
            "COH2_WEBHOOK_URL sieht nicht wie eine Discord-Webhook-URL aus "
            "(https://discord.com/api/webhooks/<id>/<token>)"
        )
    return url


def _mit_pfad(url: str, pfad: str = "", **parameter: str) -> str:
    teile = urllib.parse.urlsplit(url)
    abfrage = urllib.parse.parse_qsl(teile.query)
    abfrage.extend(parameter.items())
    return urllib.parse.urlunsplit(
        (teile.scheme, teile.netloc, teile.path.rstrip("/") + pfad, urllib.parse.urlencode(abfrage), "")
    )


def _anfrage(methode: str, url: str, nutzlast: dict, *, fehlt_ist_nachricht: bool) -> dict | None:
    anfrage = urllib.request.Request(
        url,
        data=json.dumps(nutzlast).encode("utf-8"),
        method=methode,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    for versuch in range(1, VERSUCHE + 1):
        try:
            with urllib.request.urlopen(anfrage, timeout=TIMEOUT_SEKUNDEN) as antwort:
                inhalt = antwort.read()
            return json.loads(inhalt) if inhalt else None
        except urllib.error.HTTPError as fehler:
            if fehler.code == 429 and versuch < VERSUCHE:
                try:
                    warten = float(json.loads(fehler.read() or b"{}").get("retry_after", 1))
                except (ValueError, AttributeError):
                    warten = 1.0
                time.sleep(min(max(warten, 0.5), 10.0))
                continue
            if fehler.code == 404 and fehlt_ist_nachricht:
                raise NachrichtFehlt("Ranglisten-Nachricht existiert nicht mehr") from None
            if fehler.code in (401, 403, 404):
                raise WebhookFehler(
                    f"Discord lehnt den Webhook ab (HTTP {fehler.code}) - geloescht oder URL falsch?"
                ) from None
            raise WebhookFehler(f"Discord antwortet mit HTTP {fehler.code}") from None
        except urllib.error.URLError as fehler:
            raise WebhookFehler(f"Discord nicht erreichbar: {fehler.reason}") from None
    raise WebhookFehler("Discord drosselt (HTTP 429), spaeter erneut")


def _nutzlast(nachricht: dict | str) -> dict:
    """Text oder fertige Nachricht ({"content", "embeds"}) -> Webhook-Nutzlast.

    Ohne "embeds" wird beim Bearbeiten ein frueheres Embed nicht geloescht,
    ohne "content" ein frueherer Text nicht - deshalb beides immer setzen."""
    if isinstance(nachricht, str):
        nachricht = {"content": nachricht}
    nutzlast = {"content": "", "embeds": [], **nachricht}
    # Keine @-Erwaehnungen ausloesen, egal was im Text steht.
    nutzlast["allowed_mentions"] = {"parse": []}
    return nutzlast


def senden(url: str, nachricht: dict | str) -> str:
    """Neue Nachricht, gibt ihre ID zurueck."""
    antwort = _anfrage("POST", _mit_pfad(url, wait="true"), _nutzlast(nachricht), fehlt_ist_nachricht=False)
    if not antwort or "id" not in antwort:
        raise WebhookFehler("Discord hat keine Nachrichten-ID zurueckgegeben")
    return str(antwort["id"])


def bearbeiten(url: str, nachricht_id: str, nachricht: dict | str) -> None:
    _anfrage(
        "PATCH",
        _mit_pfad(url, f"/messages/{int(nachricht_id)}"),
        _nutzlast(nachricht),
        fehlt_ist_nachricht=True,
    )
