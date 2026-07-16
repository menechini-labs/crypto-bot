"""TDD: regras de gestão de risco (sem ordem real envolvida)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.risk import RiskManager


class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.r = RiskManager(max_position_pct=0.5, stop_loss_pct=0.05, take_profit_pct=0.10)

    def test_position_size_respects_cap(self):
        # caixa 1000, cap 50% => máx 500 de notional
        size = self.r.max_notional(cash=1000.0)
        self.assertAlmostEqual(size, 500.0)

    def test_stop_loss_triggered(self):
        # comprou a 100, agora 94 (-6%) => stop de 5% acionado
        self.assertTrue(self.r.should_stop_loss(entry=100.0, current=94.0))

    def test_stop_loss_not_triggered(self):
        self.assertFalse(self.r.should_stop_loss(entry=100.0, current=97.0))

    def test_take_profit_triggered(self):
        self.assertTrue(self.r.should_take_profit(entry=100.0, current=111.0))

    def test_take_profit_not_triggered(self):
        self.assertFalse(self.r.should_take_profit(entry=100.0, current=108.0))


if __name__ == "__main__":
    unittest.main()
