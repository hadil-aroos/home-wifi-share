#!/usr/bin/env bash
# Install cloudflared (official release) and a systemd service that keeps a quick tunnel to a local
# port running across reboots.   bash linux/install_tunnel.sh 8851
# Point it at wifi_share.py's port (or any app that has its own login) - never at an unprotected app.
set -euo pipefail
PORT="${1:?usage: bash linux/install_tunnel.sh <local port>}"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
cd "$(dirname "$0")"
if ! command -v cloudflared >/dev/null; then
  echo "==> Installing cloudflared (official Cloudflare release)"
  case "$(dpkg --print-architecture)" in
    arm64) PKG=cloudflared-linux-arm64.deb ;;
    amd64) PKG=cloudflared-linux-amd64.deb ;;
    *) echo "unsupported architecture"; exit 1 ;;
  esac
  curl -fsSL -o /tmp/cloudflared.deb "https://github.com/cloudflare/cloudflared/releases/latest/download/${PKG}"
  $SUDO dpkg -i /tmp/cloudflared.deb >/dev/null && rm -f /tmp/cloudflared.deb
fi
sed "s#@PORT@#${PORT}#g; s#@USER@#$(id -un)#g" cloudflare-tunnel.service.in \
  | $SUDO tee /etc/systemd/system/cloudflare-tunnel.service >/dev/null
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now cloudflare-tunnel
echo "==> Tunnel running. Get the address with: bash linux/tunnel_link.sh"