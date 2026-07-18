"""TDD: testes do paper wallet e regras de segurança.

Estes testes DEVEM passar antes de qualquer código de execução existir.
Regras críticas:
- Nunca envia ordem real (módulo execution é só simulação).
- Não compra se não há caixa suficiente.
- Não vende posição inexistente.
- Taxa é descontada em toda operação.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wallet import PaperWallet


class TestPaperWallet(unittest.TestCase):
    def setUp(self):
        self.w = PaperWallet(initial_cash=1000.0, fee_pct=0.001)

    def test_initial_cash(self):
        self.assertAlmostEqual(self.w.cash, 1000.0)
        self.assertEqual(self.w.positions, {})

    def test_buy_deducts_cash_and_charges_fee(self):
        # compra 100 USDT de BTC a 50_000
        qty = self.w.buy('BTC/USDT', price=50000.0, notional=100.0)
        # notional * (1 - fee) / price
        expected_qty = 100.0 * (1 - 0.001) / 50000.0
        self.assertAlmostEqual(qty, expected_qty)
        # caixa restante = 1000 - 100
        self.assertAlmostEqual(self.w.cash, 900.0)
        self.assertIn('BTC/USDT', self.w.positions)

    def test_buy_rejects_insufficient_cash(self):
        with self.assertRaises(ValueError):
            self.w.buy('BTC/USDT', price=50000.0, notional=2000.0)

    def test_sell_without_position_raises(self):
        with self.assertRaises(ValueError):
            self.w.sell('BTC/USDT', price=50000.0)

    def test_sell_realizes_pnl_and_charges_fee(self):
        self.w.buy('BTC/USDT', price=50000.0, notional=100.0)
        # vende tudo a 55000 (lucro de 10%)
        proceeds = self.w.sell('BTC/USDT', price=55000.0)
        # recebe qty * price * (1 - fee)
        qty = 100.0 * (1 - 0.001) / 50000.0
        expected = qty * 55000.0 * (1 - 0.001)
        self.assertAlmostEqual(proceeds, expected)
        self.assertNotIn('BTC/USDT', self.w.positions)
        # caixa final = 900 + proceeds (maior que 900 => lucro)
        self.assertGreater(self.w.cash, 900.0)

    def test_position_value(self):
        self.w.buy('BTC/USDT', price=50000.0, notional=100.0)
        val = self.w.position_value('BTC/USDT', current_price=52000.0)
        qty = 100.0 * (1 - 0.001) / 50000.0
        self.assertAlmostEqual(val, qty * 52000.0)

    def test_equity(self):
        self.w.buy('BTC/USDT', price=50000.0, notional=100.0)
        eq = self.w.equity(current_prices={'BTC/USDT': 52000.0})
        qty = 100.0 * (1 - 0.001) / 50000.0
        self.assertAlmostEqual(eq, 900.0 + qty * 52000.0)

    def test_total_equity_default_uses_avg_price(self):
        w = PaperWallet(initial_cash=1000.0, fee_pct=0.0)
        w.buy('BTC/USDT', price=50000.0, notional=100.0)
        # sem preco atual, usa avg_price -> equity == caixa inicial
        self.assertAlmostEqual(w.total_equity(), 1000.0, places=6)

    def test_total_equity_with_prices(self):
        self.w.buy('BTC/USDT', price=50000.0, notional=100.0)
        # preco sobe -> posicao vale mais
        eq = self.w.total_equity(prices={'BTC/USDT': 52000.0})
        qty = 100.0 * (1 - 0.001) / 50000.0
        self.assertAlmostEqual(eq, 900.0 + qty * 52000.0, places=6)

    def test_cycle_counter_default(self):
        w = PaperWallet(initial_cash=1000.0)
        self.assertEqual(w._cycle, 0)


if __name__ == '__main__':
    unittest.main()
