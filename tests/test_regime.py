"""TDD: seletor de estrategia por regime de mercado.

Permite que o bot auto-troque a estrategia conforme o regime:
- alta forte  -> grid_dynamic (recentraliza e compra quedas intratrend)
- lateral     -> grid (estatico, estavel)
- queda forte -> combined (ou hold) para limitar dano

Regras testaveis:
- detecta regime a partir de closes (sem look-ahead no uso real).
- retorna nome de estrategia valida.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.regime import detect_regime, select_strategy


class TestRegime(unittest.TestCase):
    def test_uptrend_selects_dynamic_grid(self):
        # subida de 100 -> 200 (alta forte)
        closes = [100.0 * (1.002 ** i) for i in range(120)]
        self.assertEqual(select_strategy(closes), "grid_dynamic")

    def test_downtrend_selects_combined(self):
        # queda de 200 -> 100 (forte)
        closes = [200.0 * (0.998 ** i) for i in range(120)]
        self.assertEqual(select_strategy(closes), "combined")

    def test_lateral_selects_grid(self):
        # oscila em torno de 100 com baixa variacao
        closes = [100.0 + 2.0 * ((i % 10) - 5) for i in range(120)]
        self.assertEqual(select_strategy(closes), "grid")

    def test_detect_regime_returns_valid(self):
        for regime in ("uptrend", "downtrend", "lateral"):
            closes = (
                [100.0 * (1.002 ** i) for i in range(120)]
                if regime == "uptrend"
                else [200.0 * (0.998 ** i) for i in range(120)]
                if regime == "downtrend"
                else [100.0 + 2.0 * ((i % 10) - 5) for i in range(120)]
            )
            detected = detect_regime(closes)
            self.assertIn(detected, ("uptrend", "downtrend", "lateral"))

    def test_invalid_closes_raises(self):
        with self.assertRaises(ValueError):
            detect_regime([])


if __name__ == "__main__":
    unittest.main()
