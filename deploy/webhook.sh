#!/usr/bin/env bash
# Discord-Webhook auf dem Pi setzen oder ersetzen (Git Bash am PC):
#   bash deploy/webhook.sh
# Die URL wird verdeckt abgefragt und per stdin uebertragen - sie landet so
# weder in der Shell-History noch in der Prozessliste des Pi.
set -euo pipefail

PI="${PI:-coh@raspi}"
NAME=coh2-sonntagsladder

read -rsp "Discord-Webhook-URL (wird nicht angezeigt): " URL
echo
case "$URL" in
    https://discord.com/api/webhooks/*|https://discordapp.com/api/webhooks/*) ;;
    *) echo "Das sieht nicht wie eine Discord-Webhook-URL aus."; exit 1 ;;
esac

printf '# Discord-Webhook des CoH2-Kanals, gesetzt per deploy/webhook.sh\nCOH2_WEBHOOK_URL=%s\n' "$URL" \
    | ssh "$PI" "sudo install -d -m 700 /etc/$NAME && sudo sh -c 'umask 077; cat > /etc/$NAME/webhook.env' && sudo systemctl start $NAME.service; sudo journalctl -u $NAME -n 3 --no-pager -o cat"
