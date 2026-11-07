"""End-to-end test of wifi_share.py (python test_wifi_share.py): a fake app on 127.0.0.1,
the proxy on this PC's Wi-Fi address. Needs a network connection (Wi-Fi or Ethernet)."""
import http.client
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wifi_share  # noqa: E402

APP, LISTEN, KEY = 18123, 18923, "test-key-1234567890"
seen_cookies = []


class App(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        seen_cookies.append(self.headers.get("Cookie"))
        if self.path.startswith("/stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for i in range(3):
                self.wfile.write(f"data: {i}\n\n".encode())
                self.wfile.flush()
                time.sleep(0.2)
            return
        body = b"hello from the app"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = b"posted:" + self.rfile.read(n) + b" hdr:" + (self.headers.get("X-VC") or "").encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


app = ThreadingHTTPServer(("127.0.0.1", APP), App)
threading.Thread(target=app.serve_forever, daemon=True).start()
proxy = ThreadingHTTPServer(("0.0.0.0", LISTEN), wifi_share.make_handler(APP, KEY))
proxy.daemon_threads = True
threading.Thread(target=proxy.serve_forever, daemon=True).start()
ip = wifi_share.lan_ip()
print("LAN address:", ip)
assert ip != "127.0.0.1", "no Wi-Fi address found"


def req(method, path, headers=None, body=None, host=ip, port=LISTEN):
    c = http.client.HTTPConnection(host, port, timeout=10)
    c.request(method, path, body, headers or {})
    r = c.getresponse()
    data = r.read()
    return r.status, dict(r.getheaders()), data


st, _, _ = req("GET", "/")
print("no key ->", st); assert st == 401
st, _, _ = req("GET", "/?key=wrong-key-000000000")
print("wrong key ->", st); assert st == 401
st, h, _ = req("GET", "/page?x=1&key=" + KEY)
cookie = h.get("Set-Cookie", "").split(";")[0]
print("right key ->", st, "redirect to", h.get("Location"), "| cookie set:", cookie.startswith("wifishare="))
assert st == 303 and h["Location"] == "/page?x=1" and cookie
st, _, data = req("GET", "/page?x=1", {"Cookie": cookie + "; theme=dark"})
print("with cookie ->", st, data); assert st == 200 and data == b"hello from the app"
assert seen_cookies[-1] == "theme=dark", seen_cookies[-1]
print("key not passed to the app: ok (app saw cookie:", seen_cookies[-1], ")")
st, _, data = req("POST", "/api", {"Cookie": cookie, "X-VC": "1", "Content-Type": "application/json"}, b'{"a":1}')
print("POST ->", st, data); assert data == b'posted:{"a":1} hdr:1'
t0 = time.time()
st, _, data = req("GET", "/stream", {"Cookie": cookie})
print("stream ->", st, data.decode().split()); assert data.count(b"data:") == 3
st, _, _ = req("GET", "/", host="127.0.0.1")
print("from this PC without key ->", st); assert st == 200
try:
    req("GET", "/", port=APP)
    exposed = True
except OSError:
    exposed = False
print("app reachable directly on Wi-Fi:", exposed); assert not exposed
proxy.shutdown(); app.shutdown()
st = None
try:
    p2 = ThreadingHTTPServer(("0.0.0.0", LISTEN + 1), wifi_share.make_handler(APP + 7, KEY))
    threading.Thread(target=p2.serve_forever, daemon=True).start()
    st, _, data = req("GET", "/", {"Cookie": cookie}, port=LISTEN + 1)
    p2.shutdown()
finally:
    print("app not running ->", st); assert st == 502
print("ALL WIFI SHARE TESTS PASSED")
os._exit(0)
