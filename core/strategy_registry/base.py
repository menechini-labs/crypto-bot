# core/strategy_registry/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    """Interface comum para estratégias plugáveis.

    Cada estratégia recebe a lista de closes (ou candles) e o estado da
    carteira, e devolve um sinal discreto: 'buy' | 'sell' | 'hold'.
    Estratégias NUNCA executam ordens — apenas sugerem.
    """

    name: str = "base"

    @abstractmethod
    def decide(self, closes: list[float], has_position: bool, ctx: dict[str, Any] | None = None) -> str:
        """Retorna 'buy', 'sell' ou 'hold'."""
        raise NotImplementedError

    # Hook opcional para estratégias que consomem candles em tempo real.
    async def on_new_candle(self, candles: list[dict[str, Any]]) -> None:  # pragma: no cover
        return None
