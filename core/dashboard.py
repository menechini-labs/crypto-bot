"""Dashboard HTTP local (stdlib, sem deps).

Expoe data/equity.json via HTTP + frontend React estatico (Vite build)
para observacao sem CLI.

Uso:
  python3 cli.py --mode dashboard
"""
import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 8000
DEFAULT_STATIC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dashboard",
    "dist",
)


def build_handler(equity_path: str, static_dir: str = DEFAULT_STATIC):
    """Retorna funcao handler(path) -> (status, body_bytes, content_type).

    Testavel diretamente sem socket.
    """
    logger.info("build_handler equity_path=%s", equity_path)
    mimetypes.init()

    def handler(path: str):
        if path == "/equity":
            if os.path.exists(equity_path):
                with open(equity_path, encoding="utf-8") as f:
                    data = f.read()
            else:
                data = "[]"
            return 200, data.encode("utf-8"), "application/json"

        # static files: / -> index.html, /assets/foo.js -> dist/assets/...
        if path == "/" or path == "/index.html":
            fpath = os.path.join(static_dir, "index.html")
        else:
            fpath = os.path.join(static_dir, path.lstrip("/"))
        if os.path.exists(fpath) and os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                body = f.read()
            ctype, _ = mimetypes.guess_type(fpath)
            return 200, body, ctype or "application/octet-stream"

        return 404, b"not found", "text/plain"

    return handler


class _Handler(BaseHTTPRequestHandler):
    def _respond(self, status: int, body: bytes, ctype: str = "text/html"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        handler = self.server.equity_handler  # type: ignore[attr-defined]
        status, body, ctype = handler(self.path)
        self._respond(status, body, ctype)

    def do_HEAD(self):
        self.do_GET()

    def log_message(self, *args):
        pass


class EquityServer:
    """Servidor HTTP local que expoe equity.json + frontend React."""

    def __init__(
        self,
        equity_path: str,
        host: str = "localhost",
        port: int = DEFAULT_PORT,
        static_dir: str = DEFAULT_STATIC,
    ):
        self.equity_path = equity_path
        self.host = host
        self.port = port
        self.static_dir = static_dir
        self._httpd = None

    def _make_server(self):
        handler_fn = build_handler(self.equity_path, self.static_dir)

        class _H(_Handler):
            pass

        httpd = ThreadingHTTPServer((self.host, self.port), _H)
        httpd.equity_handler = handler_fn  # type: ignore[attr-defined]
        return httpd

    def serve_forever(self):
        self._httpd = self._make_server()
        url = f"http://{self.host}:{self.port}"
        print(f"Dashboard em {url}  (Ctrl+C para parar)")
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard encerrado.")

    def shutdown(self):
        if self._httpd:
            self._httpd.shutdown()
