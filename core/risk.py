"""Gestão de risco (somente lógica, sem ordem real).

Limites:
- max_position_pct: fração máxima do caixa numa única posição.
- stop_loss_pct / take_profit_pct: saída por queda/subida percentual.
"""

import logging

logger = logging.getLogger('crypto-bot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class RiskManager:
    def __init__(
        self,
        max_position_pct: float = 0.5,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.10,
    ):
        if not (0.0 < max_position_pct <= 1.0):
            raise ValueError('max_position_pct must be in (0, 1]')
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def max_notional(self, cash: float) -> float:
        return cash * self.max_position_pct

    def should_stop_loss(self, entry: float, current: float) -> bool:
        logger.info(
            'should_stop_loss entry=%.2f price=%.2f -> %s',
            entry,
            current,
            (entry <= 0 and False or (entry - current) / entry >= self.stop_loss_pct),
        )
        if entry <= 0:
            return False
        return (entry - current) / entry >= self.stop_loss_pct

    def should_take_profit(self, entry: float, current: float) -> bool:
        if entry <= 0:
            return False
        return (current - entry) / entry >= self.take_profit_pct
