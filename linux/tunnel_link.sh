#!/usr/bin/env bash
# Print the current quick-tunnel address (it changes when the tunnel restarts).
#   bash linux/tunnel_link.sh            -> https://xxxx.trycloudflare.com
#   bash linux/tunnel_link.sh <key>      -> same, with ?key=<key> for wifi_share.py
host=$(curl -s -m 5 http://127.0.0.1:20241/quicktunnel | sed -n 's/.*"hostname":"\([^"]*\)".*/\1/p')
if [ -z "$host" ]; then echo "Tunnel not ready (systemctl status cloudflare-tunnel)"; exit 1; fi
if [ -n "${1:-}" ]; then echo "https://${host}/?key=$1"; else echo "https://${host}/"; fi
echo "(private: anyone with this link can open the app)"