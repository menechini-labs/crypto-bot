"""Template: Mean-reversion day-trade strategy (reversão à média via BB + Stochastic)."""

from __future__ import annotations

from typing import Any

from ..indicators import atr, bollinger, rsi, stochastic, vwap
from .base import BaseStrategy
from .registry import register


@register('mean_reversion')
class MeanReversionStrategy(BaseStrategy):
    """Compra perto da banda inferior de Bollinger + %K oversold; vende perto da banda superior."""

    name = 'mean_reversion'

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
        bb = bollinger(closes)
        st = stochastic(closes, highs or closes, lows or closes, period=14, smooth=3)
        r = rsi(closes, 14)
        v = vwap(highs or closes, lows or closes, closes, volumes or [1.0] * len(closes))
        a = atr(highs or closes, lows or closes, closes, period=14)
        conf = 0.4
        reason = []
        oversold = (st.get('k') is not None and st['k'] < 25) or (r is not None and r < 30)
        overbought = (st.get('k') is not None and st['k'] > 75) or (r is not None and r > 70)
        if bb is not None and bb[1] is not None:
            lower, upper = bb[1], bb[2]
            if lower is not None and price <= lower and oversold:
                conf += 0.3
                reason.append('near lower BB + oversold')
            if upper is not None and price >= upper and overbought:
                conf += 0.2
                reason.append('near upper BB + overbought')
        if v is not None and price < v:
            reason.append('below VWAP')
        conf = min(1.0, conf)
        if (
            not has_position
            and oversold
            and (bb is None or bb[1] is None or price <= (bb[1] if bb[1] else price))
        ):
            return {
                'side': 'buy',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'reversion buy',
                'price': price,
                'atr': a,
            }
        if has_position and overbought:
            return {
                'side': 'sell',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'reversion sell',
                'price': price,
                'atr': a,
            }
        return {
            'side': 'hold',
            'confidence': round(conf, 3),
            'reason': '; '.join(reason) or 'no revert',
            'price': price,
            'atr': a,
        }
