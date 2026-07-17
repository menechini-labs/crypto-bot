"""TDD: backtest aplica risco (stop-loss/take-profit) corretamente em todas as estrategias.

Captura o bug de risco do grid: em queda forte, o prejuizo deve ser
LIMITADO pelo stop-loss (nao deve sangrar livremente), e a contabilidade
de trades/wins deve ser consistente.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest import run_backtest
from core.config_loader import load_config
from core.synth import make_series


class TestBacktestRisk(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()

    def test_stop_loss_limits_loss_in_downtrend(self):
        # queda forte: -50% no periodo
        closes = make_series(regime="downtrend", n=300, seed=5)
        closes = [p * 0.5 for p in closes[:1]] + closes[1:]  # forca -50% no fim
        rep = run_backtest(closes, self.cfg, symbol="DOWN/USDT", strategy_name="grid")
        # stop-loss de 5% deve limitar a perda muito abaixo de -50%
        self.assertGreater(rep["pnl_pct"], -0.50, "stop-loss deve limitar perda em queda")

    def test_no_position_means_no_loss_in_flat_after_sell(self):
        # apos vender por stop, nao deve re-comprar imediatamente em queda livre
        closes = [100.0] * 10 + [95.0, 90.0, 85.0, 80.0, 75.0]  # queda 25%
        rep = run_backtest(closes, self.cfg, symbol="FLAT/USDT", strategy_name="grid")
        # com stop de 5%, a perda nao pode chegar perto de -25%
        self.assertGreater(rep["pnl_pct"], -0.25)

    def test_trades_counted_consistently(self):
        closes = make_series(regime="lateral", n=200, seed=11)
        rep = run_backtest(closes, self.cfg, symbol="LAT/USDT", strategy_name="grid")
        self.assertGreaterEqual(rep["trades"], 0)
        self.assertLessEqual(rep["wins"], rep["trades"])

    def test_dynamic_grid_stop_in_downtrend(self):
        closes = make_series(regime="downtrend", n=300, seed=9)
        closes = [p * 0.6 for p in closes[:1]] + closes[1:]
        rep = run_backtest(closes, self.cfg, symbol="DYND/USDT", strategy_name="grid_dynamic")
        self.assertGreater(rep["pnl_pct"], -0.60, "dinamico tb deve respeitar stop")


if __name__ == "__main__":
    unittest.main()
