# Open an app running on this PC from your phone ANYWHERE (not only on your Wi-Fi), through a
# Cloudflare quick tunnel. The address is random and changes every time this script starts.
#
#   powershell -ExecutionPolicy Bypass -File phone_tunnel.ps1 -Port 8051
#
# Needs cloudflared (winget install --id Cloudflare.cloudflared).
# SECURITY: the link is reachable from the whole internet. Only tunnel an app that asks for its own
# key/password, or tunnel wifi_share.py (which adds one): run wifi_share.py --port 8051 first and
# then this script with -Port 8851, and open the printed address with ?key=... at the end.
param([int]$Port = 8851)
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) { $cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe" }
if (-not (Test-Path $cf)) { Write-Host "cloudflared not found. Install it: winget install --id Cloudflare.cloudflared"; exit 1 }
& $cf tunnel --no-autoupdate --url "http://127.0.0.1:$Port"