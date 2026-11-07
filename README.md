# Home Wi-Fi Share

Open a web app that runs on your PC (a dashboard, a control panel, anything on `127.0.0.1`) from
your phone, safely:

- **On your home Wi-Fi** with `wifi_share.py`: a small key-protected gateway. Python standard
  library only, nothing to install.
- **From anywhere** with a Cloudflare quick tunnel (`phone_tunnel.ps1` on Windows, `linux/` on a
  server), placed in front of `wifi_share.py` so the key still protects it.

## On your home Wi-Fi

1. Start your app so it listens only on this PC, for example:
   `python dashboard.py --host 127.0.0.1 --port 8051`
2. Share it:
   ```
   python wifi_share.py --port 8051
   ```
   It prints a link like `http://192.168.x.x:8851/?key=...`.
3. Open that link on your phone (same Wi-Fi). The key is then remembered in a cookie and removed from
   the address bar, so you can bookmark the page.

If Windows asks about the firewall, allow **Private networks** only.

Options: `--listen 9000` (phone port, default app port + 800), `--key ...` (your own key; otherwise
a random one is created and saved in `.share_key`, which git ignores).

## From anywhere (mobile data, another network)

```
python wifi_share.py --port 8051
powershell -ExecutionPolicy Bypass -File phone_tunnel.ps1 -Port 8851
```
Open the printed `https://....trycloudflare.com` address with `/?key=<your key>` at the end. The
address changes each time the tunnel starts.

On a Linux server (runs across reboots):
```
bash linux/install_tunnel.sh 8851
bash linux/tunnel_link.sh <your key>
```

## How it stays safe

- The app itself still listens only on `127.0.0.1`; phones only reach the gateway.
- Every request from another device needs the key (link once, then cookie). Wrong or missing key ->
  locked page. The key is compared in constant time and is never forwarded to the app.
- Visitors on the PC itself (`127.0.0.1`) don't need the key.
- Never point a tunnel at an app directly unless the app has its own login.

## Test

```
python test_wifi_share.py
```
Checks: no key / wrong key are refused, the key link sets the cookie, pages, POSTs and live
streams (Server-Sent Events) pass through, the key is not leaked to the app, and the app is not
reachable directly on the Wi-Fi.
