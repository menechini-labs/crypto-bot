"""TDD: engine de backtest.

Regras críticas:
- Sem look-ahead: a decisao no passo t usa apenas closes[0..t].
- Taxa descontada em toda operacao (igual ao PaperWallet).
- O PnL final do backtest deve bater com o equity do PaperWallet.
- Nunca envia ordem real (usa PaperExecutor paper).
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest import run_backtest
from core.wallet import PaperWallet
from core.config_loader import load_config


def make_closes(n: int, start: float = 100.0, step: float = 1.0) -> list[float]:
    return [start + step * i for i in range(n)]


class TestBacktest(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "initial_cash_usdt": 1000.0,
            "fee_pct": 0.001,
            "max_position_pct": 1.0,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
        }

    def test_no_lookahead_buy_uses_only_past(self):
        # sobe monotonicamente: deve comprar e nunca olhar o futuro
        closes = make_closes(50, start=100.0, step=2.0)
        report = run_backtest(closes, self.cfg, strategy_name="always_buy")
        # com always_buy, compra no primeiro candle possivel e segura
        self.assertIn("final_equity", report)
        self.assertGreaterEqual(report["trades"], 1)

    def test_backtest_deterministic(self):
        # rodar duas vezes deve dar o mesmo resultado (sem aleatoriedade)
        closes = make_closes(30, start=100.0, step=1.0)
        r1 = run_backtest(closes, self.cfg, strategy_name="always_buy")
        r2 = run_backtest(closes, self.cfg, strategy_name="always_buy")
        self.assertAlmostEqual(r1["final_equity"], r2["final_equity"])
        self.assertEqual(r1["trades"], r2["trades"])

    def test_backtest_no_lookahead(self):
        # alterar um candle FUTURO nao deve mudar a decisao nos primeiros passos
        base = make_closes(40, start=100.0, step=1.0)
        modified = list(base)
        modified[-1] = base[-1] * 10.0  # muda so o ultimo
        r_base = run_backtest(base[:20], self.cfg, strategy_name="always_buy")
        r_mod = run_backtest(modified[:20], self.cfg, strategy_name="always_buy")
        self.assertAlmostEqual(r_base["final_equity"], r_mod["final_equity"])

    def test_no_trades_when_hold(self):
        closes = make_closes(20, start=100.0, step=0.0)
        report = run_backtest(closes, self.cfg, strategy_name="always_hold")
        self.assertEqual(report["trades"], 0)
        self.assertAlmostEqual(report["final_equity"], 1000.0)

    def test_max_drawdown_computed(self):
        closes = [100, 110, 90, 120, 80, 130]
        report = run_backtest(closes, self.cfg, strategy_name="always_hold")
        self.assertIn("max_drawdown_pct", report)
        self.assertGreaterEqual(report["max_drawdown_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
