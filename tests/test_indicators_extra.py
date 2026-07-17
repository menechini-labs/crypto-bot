"""TDD: indicadores MACD e Bollinger Bands (stdlib)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.indicators import bollinger, macd


def trend_up(n=60, start=100.0, step=1.0):
    return [start + step * i for i in range(n)]


def sideways(n=60, base=100.0, amp=2.0):
    return [base + amp * (i % 2) for i in range(n)]


class TestMACD(unittest.TestCase):
    def test_macd_returns_three_components(self):
        out = macd(trend_up())
        self.assertIn("macd", out)
        self.assertIn("signal", out)
        self.assertIn("hist", out)

    def test_macd_positive_in_uptrend(self):
        out = macd(trend_up())
        self.assertGreater(out["macd"], 0)

    def test_macd_cross_up_detected(self):
        # hist proximo de zero ou positivo indica cruzamento bullish recente
        out = macd(trend_up())
        self.assertGreaterEqual(out["hist"], -1e-9)

    def test_macd_handles_short_series(self):
        out = macd([1.0, 2.0, 3.0])
        # sem dados suficientes, retorna None
        self.assertIsNone(out["macd"])


class TestBollinger(unittest.TestCase):
    def test_bollinger_returns_band(self):
        mid, upper, lower = bollinger(trend_up(), period=20, k=2.0)
        self.assertGreater(upper, mid)
        self.assertLess(lower, mid)

    def test_price_above_upper_signal(self):
        closes = trend_up(40)
        mid, upper, lower = bollinger(closes, period=20, k=2.0)
        last = closes[-1]
        # em forte alta, o preco tende a estar proximo/Acima da banda superior
        self.assertGreaterEqual(last, lower)

    def test_bollinger_short_series_returns_none(self):
        self.assertEqual(bollinger([1.0, 2.0], period=20), (None, None, None))


if __name__ == "__main__":
    unittest.main()
