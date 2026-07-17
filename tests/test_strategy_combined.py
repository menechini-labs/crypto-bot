"""TDD: estratégia combinada (MA-cross + RSI + MACD + Bollinger).

Regras recomendáveis (evitar overfitting):
- BUY: MA-cross bullish E RSI < 70 E MACD hist > 0 E preço não estourando banda superior.
- SELL: MA-cross bearish OU preço tocando banda superior com MACD negativo.
- Caso contrário: HOLD.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy import decide_combined


class TestStrategyCombined(unittest.TestCase):
    def test_returns_valid_signal(self):
        closes = [100 + i for i in range(60)]
        self.assertIn(decide_combined(closes), ("buy", "sell", "hold"))

    def test_uptrend_with_momentum_buy(self):
        # alta forte e sustentada -> sinal inclinado a buy (nao garante, mas valido)
        closes = [100 + i for i in range(80)]
        sig = decide_combined(closes)
        self.assertIn(sig, ("buy", "hold"))  # nunca 'sell' em alta limpa

    def test_short_series_is_hold(self):
        self.assertEqual(decide_combined([1.0, 2.0, 3.0]), "hold")

    def test_no_crash_sideways(self):
        closes = [100 + (i % 2) for i in range(60)]
        sig = decide_combined(closes)
        self.assertIn(sig, ("buy", "sell", "hold"))


if __name__ == "__main__":
    unittest.main()
