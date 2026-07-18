"""Template: Contrarian day-trade strategy (contraria extremos de momentum)."""

from __future__ import annotations

from typing import Any

from ..indicators import atr, macd, rsi, stochastic, vwap
from .base import BaseStrategy
from .registry import register


@register('contrarian')
class ContrarianStrategy(BaseStrategy):
    """Contraria exaustão: vende após RSI/MACD esticados em alta; compra após esticados em baixa."""

    name = 'contrarian'

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
        r = rsi(closes, 14)
        m = macd(closes)
        st = stochastic(closes, highs or closes, lows or closes, period=14, smooth=3)
        a = atr(highs or closes, lows or closes, closes, period=14)
        v = vwap(highs or closes, lows or closes, closes, volumes or [1.0] * len(closes))
        hist = m.get('hist') if m else None
        conf = 0.4
        reason = []
        overbought = (r is not None and r > 70) or (st.get('k') is not None and st['k'] > 80)
        oversold = (r is not None and r < 30) or (st.get('k') is not None and st['k'] < 20)
        if overbought:
            conf += 0.25
            reason.append('overbought extreme')
        if oversold:
            conf += 0.25
            reason.append('oversold extreme')
        if hist is not None:
            if hist > 0:
                conf += 0.05
            else:
                conf += 0.05 if oversold else 0.0
        conf = min(1.0, conf)
        if not has_position and oversold and (v is None or price < v):
            return {
                'side': 'buy',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'contrarian buy',
                'price': price,
                'atr': a,
            }
        if has_position and overbought:
            return {
                'side': 'sell',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'contrarian sell',
                'price': price,
                'atr': a,
            }
        return {
            'side': 'hold',
            'confidence': round(conf, 3),
            'reason': '; '.join(reason) or 'no extreme',
            'price': price,
            'atr': a,
        }
