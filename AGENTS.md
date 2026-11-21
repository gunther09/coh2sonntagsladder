# CoH2-Sonntagsladder – Hinweise fuer Agenten und Entwickler

Was das Projekt tut und wie es betrieben wird: `README.md`.

- **Oeffentliches Repo.** Nie Geheimnisse committen: Die Discord-Webhook-URL
  enthaelt ein Token und liegt nur auf dem Pi in
  `/etc/coh2-sonntagsladder/webhook.env`. Auch nicht in Logs oder
  Fehlermeldungen ausgeben (siehe `sonntagsladder/webhook.py`).
- **Nur Standardbibliothek zur Laufzeit.** Der Pi startet den Code mit
  `/usr/bin/python3` (3.11), lokal laeuft Python 3.10 - nichts verwenden,
  was 3.11+ braucht (z.B. `tomllib`).
- **Tests vor jedem Deploy, offline:** `.venv\Scripts\python.exe -m pytest`.
  `deploy/push.sh` bricht bei roten Tests ab. Relic und Discord sind in den
  Tests Fakes (`tests/daten.py`), echter Netzzugriff laesst den Test scheitern.
- **`zustand.json` ist unersetzlich:** Relic vergisst Spiele nach 10 neueren.
  Formataenderungen nur mit Versionssprung und Migration.
- Der Pi selbst (Zugaenge, Stabilitaetsregeln, Aenderungsprotokoll) ist im
  privaten Repo des Besitzers dokumentiert, nicht hier.
