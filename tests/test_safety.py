"""Safety: garante que o bot NUNCA envia ordem real sem consentimento.

Este teste é a linha de defesa em código (independente do hook `safety`
do pre-commit, que checa vulnerabilidades em dependencias).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution import PaperExecutor


class TestSafetyNoLiveByDefault(unittest.TestCase):
    def test_default_is_paper(self):
        self.assertEqual(PaperExecutor().mode, "paper")

    def test_live_blocked_without_env(self):
        # garante que mesmo por engano ninguem liga live
        if "ALLOW_LIVE_TRADING" in os.environ:
            del os.environ["ALLOW_LIVE_TRADING"]
        with self.assertRaises(RuntimeError):
            PaperExecutor(mode="live")

    def test_live_requires_explicit_env(self):
        os.environ["ALLOW_LIVE_TRADING"] = "1"
        try:
            ex = PaperExecutor(mode="live")
            self.assertEqual(ex.mode, "live")
        finally:
            del os.environ["ALLOW_LIVE_TRADING"]

    def test_no_network_call_in_paper_buy(self):
        # execute_buy em paper nao pode depender de rede/exchange
        ex = PaperExecutor(mode="paper")
        fill = ex.execute_buy("BTC/USDT", 50000.0, 100.0)
        self.assertFalse(fill.get("live", False))
        self.assertEqual(fill["status"], "simulated")


if __name__ == "__main__":
    unittest.main()
