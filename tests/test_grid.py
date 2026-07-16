"""TDD: estratégia Grid (compra/venda em faixas de preço).

Grid opera em mercado lateral: divide um range em níveis. Quando o preço
cai a um nível, compra; quando sobe ao nível acima, venda o que comprou.
Sem look-ahead: a decisão em t usa apenas closes[0..t].

Regras testadas:
- Níveis são gerados a partir de um range e quantidade.
- decide_grid retorna 'buy' quando preço cruza nível para baixo (entre níveis).
- decide_grid retorna 'sell' quando preço cruza nível para cima e há posição.
- Em range estreito, alterna buy/sell conforme o preço oscila.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy import build_grid, decide_grid


class TestBuildGrid(unittest.TestCase):
    def test_grid_levels_count(self):
        levels = build_grid(low=100.0, high=200.0, n=5)
        # n=5 gera 5 níveis (sem contar extremos ou incluindo)
        self.assertEqual(len(levels), 5)
        self.assertEqual(levels[0], 100.0)
        self.assertEqual(levels[-1], 200.0)

    def test_grid_sorted_ascending(self):
        levels = build_grid(low=50.0, high=150.0, n=10)
        self.assertEqual(levels, sorted(levels))


class TestDecideGrid(unittest.TestCase):
    def setUp(self):
        self.levels = build_grid(low=100.0, high=200.0, n=5)

    def test_buy_when_price_drops_to_lower_level(self):
        # niveis: [100,125,150,175,200]; 128->118 cruza de 125+ para 100-
        closes = [122.0, 128.0, 118.0]
        sig = decide_grid(closes, self.levels, has_position=False)
        self.assertEqual(sig, "buy")

    def test_no_buy_if_already_have_position(self):
        closes = [122.0, 128.0, 118.0]
        sig = decide_grid(closes, self.levels, has_position=True)
        self.assertEqual(sig, "hold")

    def test_sell_when_price_rises_with_position(self):
        # 128->158 cruza de faixa 125+ para 150+
        closes = [118.0, 128.0, 158.0]
        sig = decide_grid(closes, self.levels, has_position=True)
        self.assertEqual(sig, "sell")

    def test_hold_in_middle_no_cross(self):
        closes = [150.0, 150.0, 150.0]
        sig = decide_grid(closes, self.levels, has_position=False)
        self.assertEqual(sig, "hold")

    def test_short_series_is_hold(self):
        self.assertEqual(decide_grid([100.0, 101.0], self.levels, False), "hold")


if __name__ == "__main__":
    unittest.main()
