#!/usr/bin/env bash
# CoH2-Sonntagsladder auf dem Raspberry Pi einrichten bzw. aktualisieren.
# Aufruf (auf dem Pi):  sudo bash deploy/deploy.sh <quellverzeichnis>
# Normalerweise ueber deploy/push.sh vom Windows-PC aus. Idempotent.
set -euo pipefail

SRC="${1:-/tmp/coh2-sonntagsladder-src}"
NAME=coh2-sonntagsladder
BENUTZER=coh2ladder
APP=/opt/$NAME/app
ETC=/etc/$NAME
STATE=/var/lib/$NAME

[ -d "$SRC/sonntagsladder" ] && [ -f "$SRC/deploy/$NAME.service" ] \
    || { echo "Quellverzeichnis $SRC unvollstaendig"; exit 1; }

# --- Benutzer + Verzeichnisse -------------------------------------------------
id "$BENUTZER" &>/dev/null || useradd --system --home-dir "$STATE" \
    --shell /usr/sbin/nologin "$BENUTZER"

install -d -m 755 "/opt/$NAME" "$APP"
install -d -m 700 "$ETC"
install -d -o "$BENUTZER" -g "$BENUTZER" -m 750 "$STATE"

# --- Code (nur Standardbibliothek, kein venv) ---------------------------------
rm -rf "$APP/sonntagsladder"
cp -r "$SRC/sonntagsladder" "$APP/sonntagsladder"
find "$APP" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
chmod -R u=rwX,go=rX "$APP"
python3 -m compileall -q "$APP/sonntagsladder"

# --- Webhook: Geheimnis, nur hier, nie im Repo --------------------------------
# systemd liest die Datei als root, der Dienstbenutzer braucht keinen Zugriff.
if [ ! -f "$ETC/webhook.env" ]; then
    ( umask 077; cat > "$ETC/webhook.env" <<'EOF'
# Discord-Webhook des CoH2-Kanals (Kanal -> Einstellungen -> Integrationen ->
# Webhooks). Setzen am bequemsten vom PC aus: bash deploy/webhook.sh
# Ohne URL sammelt der Dienst nur Spiele und meldet nichts.
# COH2_WEBHOOK_URL=https://discord.com/api/webhooks/<id>/<token>
EOF
    )
    echo "Vorlage angelegt: $ETC/webhook.env (noch ohne Webhook)"
fi
chown root:root "$ETC/webhook.env"
chmod 600 "$ETC/webhook.env"

# --- systemd ------------------------------------------------------------------
install -m 644 "$SRC/deploy/$NAME.service" "$SRC/deploy/$NAME.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now "$NAME.timer"

# Einmal sofort laufen lassen. Ein Fehler hier bricht das Deployment nicht ab,
# der Timer versucht es in 15 Minuten wieder.
echo "Lauf ..."
systemctl start "$NAME.service" || echo "WARNUNG: Lauf fehlgeschlagen, siehe journalctl -u $NAME"
journalctl -u "$NAME" -n 5 --no-pager -o cat || true
echo
systemctl list-timers "$NAME.timer" --no-pager | sed -n 1,2p
