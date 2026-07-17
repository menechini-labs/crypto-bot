# core/strategy_registry/grid_strategy.py
from .base import BaseStrategy
from .registry import register

@register("grid")
class GridStrategy(BaseStrategy):
    """Estratégia Grid Estática."""

    def decide(self, closes: list[float], has_position: bool) -> str:
        if not has_position:
            return "buy"
        midpoint = sum(closes[-5:]) / 5
        latest = closes[-1]
        if latest < midpoint:
            return "buy"
        elif latest > midpoint:
            return "sell"
        return "hold"
