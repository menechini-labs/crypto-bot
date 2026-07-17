"""TDD: gerador de séries sintéticas para backtest multi-regime.

Permite testar estratégias em regimes reproduzíveis (sem rede):
- lateral: oscila em torno de um preço (grid brilha).
- uptrend: tendência de alta forte (baseline tende a ganhar).
- downtrend: tendência de queda forte (grid estático sofre).

Regras:
- deterministico com seed.
- retorna lista de closes (preços positivos).
- comprimento respeitado.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.synth import make_series


class TestSynth(unittest.TestCase):
    def test_length(self):
        s = make_series(regime="lateral", n=200, seed=42)
        self.assertEqual(len(s), 200)

    def test_deterministic_with_seed(self):
        a = make_series(regime="lateral", n=100, seed=7)
        b = make_series(regime="lateral", n=100, seed=7)
        self.assertEqual(a, b)

    def test_prices_positive(self):
        for regime in ("lateral", "uptrend", "downtrend"):
            s = make_series(regime=regime, n=150, seed=1)
            self.assertTrue(all(p > 0 for p in s), f"{regime} tem preco <= 0")

    def test_uptrend_ends_higher(self):
        s = make_series(regime="uptrend", n=300, seed=3)
        self.assertGreater(s[-1], s[0])

    def test_downtrend_ends_lower(self):
        s = make_series(regime="downtrend", n=300, seed=3)
        self.assertLess(s[-1], s[0])

    def test_invalid_regime(self):
        with self.assertRaises(ValueError):
            make_series(regime="explode", n=10, seed=1)


if __name__ == "__main__":
    unittest.main()
