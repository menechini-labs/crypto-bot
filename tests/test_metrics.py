"""TDD: metricas de qualidade do backtest.

compute_metrics(equity_curve, periods_per_year) -> sharpe, cagr, max_dd, win_rate.
Sem numpy; implementacao stdlib.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.metrics import compute_metrics


class TestMetrics(unittest.TestCase):
    def test_flat_equity_zero_sharpe(self):
        eq = [1000.0] * 50
        m = compute_metrics(eq, periods_per_year=365 * 24)
        self.assertAlmostEqual(m['sharpe'], 0.0, places=6)
        self.assertAlmostEqual(m['cagr'], 0.0, places=6)
        self.assertAlmostEqual(m['max_drawdown'], 0.0, places=6)

    def test_rising_equity_positive_cagr(self):
        eq = [1000.0 * (1.01**i) for i in range(10)]  # sobe 1%/periodo
        m = compute_metrics(eq, periods_per_year=365)
        self.assertGreater(m['cagr'], 0.0)
        self.assertAlmostEqual(m['max_drawdown'], 0.0, places=6)

    def test_drawdown_detected(self):
        eq = [1000.0, 1100.0, 900.0, 950.0]  # pico 1100, fundo 900
        m = compute_metrics(eq, periods_per_year=365)
        self.assertAlmostEqual(m['max_drawdown'], (1100 - 900) / 1100, places=6)

    def test_sharpe_positive_for_steady_up(self):
        eq = [1000.0 + i * 5 for i in range(20)]  # sobe linear, baixa vol
        m = compute_metrics(eq, periods_per_year=365)
        self.assertGreater(m['sharpe'], 0.0)

    def test_win_rate_from_trades(self):
        eq = [1000.0, 1010.0, 1005.0, 1020.0]
        m = compute_metrics(eq, periods_per_year=365, wins=2, trades=3)
        self.assertAlmostEqual(m['win_rate'], 2 / 3, places=6)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            compute_metrics([], 365)


if __name__ == '__main__':
    unittest.main()
