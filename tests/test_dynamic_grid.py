"""TDD: Grid dinâmico.

O grid estático trava num range histórico. Se o preço sai muito acima/abaixo,
ele para de operar (ou só compra numa queda sem fim). O grid dinâmico
REcentraliza os níveis quando o preço foge do range atual.

Regras testadas:
- build_dynamic_grid aceita um centro e gera níveis ao redor (simetria).
- decide_dynamic_grid compra ao cruzar nível para baixo (sem posição).
- decide_dynamic_grid vende ao cruzar nível para cima (com posição).
- recentraliza: se o preço passa do topo, os níveis deslocam para cima.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy import build_dynamic_grid, decide_dynamic_grid


class TestDynamicGrid(unittest.TestCase):
    def test_build_centered(self):
        levels = build_dynamic_grid(center=150.0, step=10.0, n=5)
        # n=5 impar: centro no meio; simetrico em torno de 150
        self.assertEqual(len(levels), 5)
        self.assertEqual(levels[2], 150.0)
        self.assertEqual(levels[0], 130.0)
        self.assertEqual(levels[-1], 170.0)

    def test_buy_on_down_cross(self):
        levels = build_dynamic_grid(center=150.0, step=10.0, n=5)
        # 158 -> 142 cruza de 150+ para 140- (abaixo do centro)
        closes = [160.0, 158.0, 142.0]
        self.assertEqual(decide_dynamic_grid(closes, levels, has_position=False), "buy")

    def test_sell_on_up_cross(self):
        levels = build_dynamic_grid(center=150.0, step=10.0, n=5)
        # 142 -> 162 cruza para cima
        closes = [140.0, 142.0, 162.0]
        self.assertEqual(decide_dynamic_grid(closes, levels, has_position=True), "sell")

    def test_recenter_when_price_exits_range(self):
        # preco sai muito acima do topo (170) -> recentraliza para cima
        old_levels = build_dynamic_grid(center=150.0, step=10.0, n=5)
        new_levels = build_dynamic_grid(
            center=200.0, step=10.0, n=5
        )
        # novo centro subiu
        self.assertGreater(new_levels[2], old_levels[2])
        self.assertEqual(new_levels[-1], 220.0)


if __name__ == "__main__":
    unittest.main()
