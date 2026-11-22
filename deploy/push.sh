#!/usr/bin/env bash
# Vom Windows-PC (Git Bash) aus: Tests, dann Code auf den Pi und dort
# deploy.sh ausfuehren.
#   bash deploy/push.sh
# Anderer Pi/Benutzer:  PI=coh@<ip-des-pi> bash deploy/push.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PI="${PI:-coh@raspi}"
TMP=/tmp/coh2-sonntagsladder-src

# Rote Tests = kein Deployment
PYTHON=.venv/Scripts/python.exe
[ -x "$PYTHON" ] || PYTHON=.venv/bin/python
"$PYTHON" -m pytest || { echo "Tests rot - nichts deployt"; exit 1; }

# Code-Version fuer die Fusszeile: Zahl der Commits und Datum des letzten.
# Nicht committete Aenderungen bekommen ein "+" (Stand ist dann nicht im Repo).
VERSION="$(git rev-list --count HEAD)"
[ -z "$(git status --porcelain)" ] || VERSION="$VERSION+"
printf '%s %s\n' "$VERSION" "$(git log -1 --format=%cd --date=format:%d.%m.%Y)" \
    > sonntagsladder/version.txt
echo "Code-Version $(cat sonntagsladder/version.txt)"

tar czf - --exclude=__pycache__ sonntagsladder deploy \
    | ssh "$PI" "umask 077 && rm -rf $TMP && mkdir -m 700 $TMP && tar xzf - -C $TMP"
ssh "$PI" "sudo bash $TMP/deploy/deploy.sh $TMP; rc=\$?; rm -rf $TMP; exit \$rc"
