"""Share a web app running on this PC with phones on your home Wi-Fi, protected by a secret key.

    python wifi_share.py --port 8051            # share http://127.0.0.1:8051 on the Wi-Fi
    python wifi_share.py --port 8060 --listen 8861

The app itself keeps listening only on 127.0.0.1 (this PC). This tool listens on the Wi-Fi and
forwards to it, but only for visitors who opened the link with the key once (it is then kept in a
cookie). Streaming responses (live charts, Server-Sent Events) are passed through as they arrive.

The key is created on first run and stored in .share_key next to this file (never commit it).
Standard library only - no packages to install.
"""
import argparse
import http.client
import os
import secrets
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlencode, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, ".share_key")
COOKIE = "wifishare"
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
       "trailers", "transfer-encoding", "upgrade", "host", "content-length"}


def lan_ip():
    """This PC's address on the home network (the one phones use). Nothing is sent."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 80))      # any private address; UDP connect only picks the route
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def load_key(explicit=None):
    """--key / WIFI_SHARE_KEY, else the saved key, else a new random one (saved, so links keep working)."""
    key = explicit or os.getenv("WIFI_SHARE_KEY", "").strip()
    if key:
        return key
    try:
        with open(KEY_FILE) as f:
            key = f.read().strip()
    except OSError:
        key = ""
    if len(key) < 16:
        key = secrets.token_urlsafe(18)
        with open(KEY_FILE, "w") as f:
            f.write(key)
    return key


def make_handler(target_port, key):
    class Proxy(BaseHTTPRequestHandler):
        server_version = "wifi-share"

        def log_message(self, *a):
            pass

        def _cookie_key(self):
            for part in (self.headers.get("Cookie") or "").split(";"):
                name, _, value = part.strip().partition("=")
                if name == COOKIE:
                    return value
            return ""

        def _deny(self):
            body = (b"<!doctype html><meta name=viewport content='width=device-width'>"
                    b"<p style='font:16px system-ui;padding:24px'>Locked. Open the full link printed on the PC "
                    b"(the one ending in <code>?key=...</code>).</p>")
            self.send_response(401)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _forward(self):
            url = urlsplit(self.path)
            query = parse_qsl(url.query, keep_blank_values=True)
            given = next((v for k, v in query if k == "key"), "")
            local = self.client_address[0] in ("127.0.0.1", "::1")
            if given and secrets.compare_digest(given, key):
                # first visit with the link: remember the key in a cookie and drop it from the address bar
                rest = urlencode([(k, v) for k, v in query if k != "key"])
                self.send_response(303)
                self.send_header("Set-Cookie", f"{COOKIE}={key}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Strict")
                self.send_header("Location", url.path + (f"?{rest}" if rest else ""))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if not local and not secrets.compare_digest(self._cookie_key(), key):
                return self._deny()

            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
            cookies = [c for c in (self.headers.get("Cookie") or "").split(";")
                       if c.strip() and not c.strip().startswith(COOKIE + "=")]
            headers.pop("Cookie", None)
            if cookies:
                headers["Cookie"] = ";".join(cookies)        # never pass our key on to the app
            headers["Host"] = f"127.0.0.1:{target_port}"
            conn = http.client.HTTPConnection("127.0.0.1", target_port, timeout=120)
            try:
                conn.request(self.command, self.path, body, headers)
                resp = conn.getresponse()
            except OSError:
                msg = f"Nothing is running on this PC at port {target_port}.".encode()
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
                return
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() not in HOP or k.lower() == "content-length":
                    self.send_header(k, v)
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                while True:                                    # stream (keeps live updates live)
                    chunk = resp.read1(16384)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except OSError:
                pass                                           # phone closed the page
            finally:
                conn.close()
                self.close_connection = True

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _forward

    return Proxy


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, required=True, help="port of the app on this PC (127.0.0.1:PORT)")
    ap.add_argument("--listen", type=int, default=None, help="port phones connect to (default: PORT + 800)")
    ap.add_argument("--key", default=None, help="use this key instead of the saved random one")
    args = ap.parse_args(argv)
    listen = args.listen or args.port + 800
    key = load_key(args.key)
    srv = ThreadingHTTPServer(("0.0.0.0", listen), make_handler(args.port, key))
    srv.daemon_threads = True
    print(f"Sharing http://127.0.0.1:{args.port} on your Wi-Fi.")
    print(f"On your phone (same Wi-Fi), open:  http://{lan_ip()}:{listen}/?key={key}")
    print("Anyone with this link on your network can open the app. Ctrl+C to stop.")
    if os.name == "nt":
        print("(If Windows asks about the firewall, allow Private networks only.)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
