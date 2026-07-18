# core/strategy_registry/dynamic_grid_strategy.py
from .base import BaseStrategy
from .registry import register


@register('grid_dynamic')
class DynamicGridStrategy(BaseStrategy):
    """Estratégia Grid Dinâmica: ajusta níveis dinamicamente."""

    def decide(self, closes: list[float], has_position: bool, ctx=None) -> str:
        if len(closes) < 2:
            return 'hold'
        if not has_position:
            return 'buy'

        center = closes[-2]
        latest = closes[-1]
        # Passo dinâmico a partir da variação recente (evita div por zero)
        step = max(abs(latest - center), 1e-8)
        grid_levels = [center - (step * i) for i in range(5, -1, -1)]

        for level in grid_levels:
            if latest < level:  # Compra se abaixo do grid
                return 'buy'
            elif latest > level:  # Venda se acima do grid
                return 'sell'
        return 'hold'
