"""Template: Breakout day-trade strategy (volatility breakout via ATR + range)."""

from __future__ import annotations

from typing import Any

from ..indicators import atr, bollinger, vwap
from .base import BaseStrategy
from .registry import register


@register('breakout')
class BreakoutStrategy(BaseStrategy):
    """Compra quando preço rompe máxima recente + ATR confirma expansão de vol; vende no retorno ao VWAP."""

    name = 'breakout'

    def decide(
        self, closes: list[float], has_position: bool = False, ctx: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        ctx = ctx or {}
        candles = ctx.get('candles') or []
        highs = [c['high'] for c in candles] if candles else (ctx.get('highs') or [])
        lows = [c['low'] for c in candles] if candles else (ctx.get('lows') or [])
        volumes = [c['volume'] for c in candles] if candles else (ctx.get('volumes') or [])
        closes = (closes or [c['close'] for c in candles]) if candles else closes
        if len(closes) < 15:
            return {'side': 'hold', 'confidence': 0.0, 'reason': 'series too short'}
        price = closes[-1]
        lookback = highs[-15:-1] if highs else closes[-15:-1]
        recent_high = max(lookback) if lookback else price
        a = atr(highs or closes, lows or closes, closes, period=14)
        v = vwap(highs or closes, lows or closes, closes, volumes or [1.0] * len(closes))
        bb = bollinger(closes)
        conf = 0.5
        reason = []
        if price > recent_high:
            conf += 0.25
            reason.append(f'break above {recent_high:.2f}')
        if a is not None and bb is not None and bb[1] is not None:
            # banda largura relativa como proxy de vol
            width = (bb[2] - bb[1]) / (bb[1] if bb[1] else 1.0)
            if width > 0.01:
                conf += 0.1
                reason.append('vol expansion')
        conf = min(1.0, conf)
        if not has_position and price > recent_high and (a is None or a > 0):
            return {
                'side': 'buy',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'breakout buy',
                'price': price,
                'atr': a,
            }
        if has_position and v is not None and price < v:
            return {
                'side': 'sell',
                'confidence': round(conf, 3),
                'reason': 'fell below VWAP',
                'price': price,
                'atr': a,
            }
        return {
            'side': 'hold',
            'confidence': round(conf, 3),
            'reason': '; '.join(reason) or 'no breakout',
            'price': price,
            'atr': a,
        }
