"""Template: Range-bound day-trade strategy (compra no suporte, vende na resistência)."""

from __future__ import annotations

from typing import Any

from ..indicators import atr, stochastic, vwap
from .base import BaseStrategy
from .registry import register


@register('range_bound')
class RangeBoundStrategy(BaseStrategy):
    """Opera faixa lateral: compra perto do suporte (BB inferior), vende perto da resistência (BB superior)."""

    name = 'range_bound'

    def decide(
        self, closes: list[float], has_position: bool = False, ctx: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        ctx = ctx or {}
        candles = ctx.get('candles') or []
        highs = [c['high'] for c in candles] if candles else (ctx.get('highs') or [])
        lows = [c['low'] for c in candles] if candles else (ctx.get('lows') or [])
        volumes = [c['volume'] for c in candles] if candles else (ctx.get('volumes') or [])
        closes = (closes or [c['close'] for c in candles]) if candles else closes
        if len(closes) < 20:
            return {'side': 'hold', 'confidence': 0.0, 'reason': 'series too short'}
        price = closes[-1]
        st = stochastic(closes, highs or closes, lows or closes, period=14, smooth=3)
        a = atr(highs or closes, lows or closes, closes, period=14)
        v = vwap(highs or closes, lows or closes, closes, volumes or [1.0] * len(closes))
        # Suporte/resistência por mín/máx recente
        support = min(lows[-20:]) if lows else min(closes[-20:])
        resistance = max(highs[-20:]) if highs else max(closes[-20:])
        conf = 0.45
        reason = []
        near_support = price <= support * 1.002 and (st.get('k') is None or st['k'] < 40)
        near_resist = price >= resistance * 0.998 and (st.get('k') is None or st['k'] > 60)
        if near_support:
            conf += 0.2
            reason.append(f'near support {support:.2f}')
        if near_resist:
            conf += 0.2
            reason.append(f'near resistance {resistance:.2f}')
        # penaliza se vwap distante (tendência)
        if v is not None and abs(price - v) / (v if v else 1.0) > 0.01:
            conf -= 0.05
        conf = min(1.0, max(0.1, conf))
        if not has_position and near_support:
            return {
                'side': 'buy',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'range buy',
                'price': price,
                'atr': a,
            }
        if has_position and near_resist:
            return {
                'side': 'sell',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'range sell',
                'price': price,
                'atr': a,
            }
        return {
            'side': 'hold',
            'confidence': round(conf, 3),
            'reason': '; '.join(reason) or 'in range',
            'price': price,
            'atr': a,
        }
