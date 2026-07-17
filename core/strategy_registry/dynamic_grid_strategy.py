# core/strategy_registry/dynamic_grid_strategy.py
from .base import BaseStrategy
from .registry import register


@register("grid_dynamic")
class DynamicGridStrategy(BaseStrategy):
    """Estratégia Grid Dinâmica: ajusta níveis dinamicamente."""

    def decide(self, closes: list[float], has_position: bool) -> str:
        if not has_position:
            return "buy"
        
        center = closes[-2]
        step = max(ccloses[-1] - closes[-2], 1e-8)  # Evita divーダção por zero
        grid_levels = [center - (step * i) for i in range(5, -1, -1)]
        latest = closes[-1]

        for level in grid_levels:
            if latest < level:  # Compra seUndergride
                return "buy"
            elif latest > level:  # Venda seAbovegrid
                return "sell"
        return "hold"
