"""TDD: dashboard HTTP local (stdlib, sem deps).

Expoe data/equity.json via HTTP + frontend React estatico (Vite build).
Testa o handler (retorna status + body + content-type) sem abrir socket.
"""
import json
import os
import sys
import unittest
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.dashboard import build_handler, EquityServer


class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.equity = os.path.join(self.tmp, "equity.json")
        with open(self.equity, "w") as f:
            json.dump(
                [
                    {"cycle": 1, "equity": 1000.0, "pnl": 0.0, "positions": {}},
                    {"cycle": 2, "equity": 1010.0, "pnl": 10.0, "positions": {}},
                ],
                f,
            )

    def test_handler_equity_returns_json(self):
        handler = build_handler(self.equity)
        status, body, ctype = handler("/equity")
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "application/json")
        data = json.loads(body)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1]["equity"], 1010.0)

    def test_handler_missing_equity_returns_empty(self):
        handler = build_handler(os.path.join(self.tmp, "nope.json"))
        status, body, ctype = handler("/equity")
        self.assertEqual(status, 200)
        self.assertEqual(ctype, "application/json")
        self.assertEqual(json.loads(body), [])

    def test_handler_404_returns_not_found(self):
        handler = build_handler(self.equity)
        status, body, ctype = handler("/nonexistent")
        self.assertEqual(status, 404)
        self.assertEqual(body, b"not found")

    def test_handler_static_html(self):
        # cria um index.html fake no static_dir
        static = tempfile.mkdtemp()
        idx = os.path.join(static, "index.html")
        with open(idx, "w") as f:
            f.write("<html>fake</html>")
        handler = build_handler(self.equity, static_dir=static)
        status, body, ctype = handler("/")
        self.assertEqual(status, 200)
        self.assertIn(b"fake", body)
        self.assertIn("html", ctype or "")

    def test_equity_server_instantiable(self):
        srv = EquityServer(self.equity, port=0)
        self.assertEqual(srv.equity_path, self.equity)


if __name__ == "__main__":
    unittest.main()
