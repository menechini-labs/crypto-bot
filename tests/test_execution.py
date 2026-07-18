"""TDD: o módulo de execução NUNCA deve enviar ordem real.

Prova que a execução é somente simulação (paper). Se alguém um dia acoplar
uma exchange real, este teste deve quebrar ou exigir flag explícita de live.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.execution import PaperExecutor


class TestPaperExecutor(unittest.TestCase):
    def setUp(self):
        self.ex = PaperExecutor(mode='paper')

    def test_executor_is_paper_only_by_default(self):
        self.assertEqual(self.ex.mode, 'paper')

    def test_buy_returns_simulated_fill_no_network(self):
        fill = self.ex.execute_buy(symbol='BTC/USDT', price=50000.0, notional=100.0)
        self.assertEqual(fill['symbol'], 'BTC/USDT')
        self.assertAlmostEqual(fill['notional'], 100.0)
        self.assertFalse(fill.get('live', False))

    def test_live_mode_rejected_without_explicit_flag(self):
        # Por segurança, live trading é bloqueado a menos que LIVE=1 seja passado.
        with self.assertRaises(RuntimeError):
            PaperExecutor(mode='live')  # deve recusar construir em live

    def test_live_requires_explicit_consent_env(self):
        import os as _os

        _os.environ['ALLOW_LIVE_TRADING'] = '1'
        try:
            ex = PaperExecutor(mode='live')
            self.assertEqual(ex.mode, 'live')
        finally:
            del _os.environ['ALLOW_LIVE_TRADING']


if __name__ == '__main__':
    unittest.main()
