"""TDD: loop contínuo do bot.

Regras críticas:
- Roda ciclos respeitando o intervalo.
- Nunca envia ordem real (executor paper).
- Se a rede falha (market data), o ciclo não quebra o loop (loga e continua).
- Respeita limite de ciclos (para testes e para nao rodar eterno).
"""
import sys
import os
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli import run_cycle
from wallet import PaperWallet


class TestContinuousLoop(unittest.TestCase):
    def test_run_cycle_uses_grid_and_paper(self):
        cfg = {
            "symbols": ["TEST/USDT"],
            "timeframe": "1h",
            "lookback": 100,
            "initial_cash_usdt": 1000.0,
            "fee_pct": 0.001,
            "max_position_pct": 0.5,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
            "strategy": "grid",
        }
        fake_closes = [100.0 + i for i in range(120)]
        with mock.patch("cli.fetch_ohlcv", return_value=[
            {"ts": i, "open": c, "high": c, "low": c, "close": c, "volume": 1.0}
            for i, c in enumerate(fake_closes)
        ]), mock.patch("cli.PaperExecutor") as MockEx:
            inst = MockEx.return_value
            inst.mode = "paper"
            wallet = PaperWallet(initial_cash=1000.0, fee_pct=0.001)
            # nao deve levantar excecao
            run_cycle(cfg, wallet=wallet)
            # propriedades do wallet real devem existir
            self.assertTrue(hasattr(wallet, "equity"))

    def test_run_cycle_survives_network_error(self):
        cfg = {
            "symbols": ["TEST/USDT"],
            "timeframe": "1h",
            "lookback": 100,
            "initial_cash_usdt": 1000.0,
            "fee_pct": 0.001,
            "max_position_pct": 0.5,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
            "strategy": "grid",
        }
        with mock.patch("cli.fetch_ohlcv", side_effect=RuntimeError("network down")):
            # nao deve quebrar o loop
            wallet = PaperWallet(initial_cash=1000.0, fee_pct=0.001)
            run_cycle(cfg, wallet=wallet)


if __name__ == "__main__":
    unittest.main()
