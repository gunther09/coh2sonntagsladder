"""Code-Version fuer die Fusszeile der Rangliste.

Die Version ist die Zahl der Commits, das Datum das des letzten Commits.
deploy/push.sh schreibt beides beim Deploy nach version.txt neben diese Datei
(nicht im Repo, steht in .gitignore). So zaehlt die Version mit jeder
Aenderung von selbst hoch. Fehlt die Datei (lokal, Tests), heisst es "dev".
"""

from __future__ import annotations

from pathlib import Path

DATEI = Path(__file__).with_name("version.txt")


def code_version(datei: Path = DATEI) -> str:
    """'code v.11, 22.11.2026' oder 'code v.dev'."""
    try:
        teile = datei.read_text(encoding="utf-8").split()
    except OSError:
        teile = []
    if len(teile) >= 2:
        return f"code v.{teile[0]}, {teile[1]}"
    return "code v.dev"
