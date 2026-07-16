"""TDD: reporter de equity/PnL (dashboard local em JSON).

Regras:
- append_equity cria o arquivo se nao existir.
- registra um registro por ciclo (timestamp, equity, pnl, positions).
- nao quebra se o arquivo estiver vazio/corrompido (recria).
- load_history retorna lista de registros.
- Tudo stdlib (sem pandas).
"""
import json
import os
import tempfile
import unittest

from reporter import append_equity, load_history, latest_equity


class TestReporter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "equity.json")

    def test_append_creates_file(self):
        self.assertFalse(os.path.exists(self.path))
        append_equity(self.path, cycle=0, equity=1000.0, pnl=0.0, positions={})
        self.assertTrue(os.path.exists(self.path))
        hist = load_history(self.path)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["equity"], 1000.0)

    def test_append_multiple_cycles(self):
        append_equity(self.path, cycle=0, equity=1000.0, pnl=0.0, positions={})
        append_equity(self.path, cycle=1, equity=1010.0, pnl=10.0, positions={"BTC/USDT": {"qty": 0.01, "avg_price": 64000.0}})
        hist = load_history(self.path)
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[1]["cycle"], 1)
        self.assertEqual(hist[1]["pnl"], 10.0)

    def test_load_history_empty_file(self):
        with open(self.path, "w") as f:
            f.write("")
        # nao deve quebrar
        self.assertEqual(load_history(self.path), [])

    def test_latest_equity(self):
        append_equity(self.path, cycle=0, equity=1000.0, pnl=0.0, positions={})
        append_equity(self.path, cycle=1, equity=1020.0, pnl=20.0, positions={})
        self.assertEqual(latest_equity(self.path), 1020.0)

    def test_latest_equity_no_file(self):
        self.assertIsNone(latest_equity(self.path))


if __name__ == "__main__":
    unittest.main()
