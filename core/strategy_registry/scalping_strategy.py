"""Template: Scalping day-trade strategy.

Wrappers finos sobre primitivas de indicadores (VWAP/ATR/Stochastic + RSI/MACD/BB)
com parâmetros pré-ajustados, espelhando o padrão populate_entry/exit do Freqtrade.
Registrado via @register("scalping").
"""

from __future__ import annotations

from typing import Any

from ..indicators import atr, rsi, stochastic, vwap
from .base import BaseStrategy
from .registry import register


@register('scalping')
class ScalpingStrategy(BaseStrategy):
    """Scalping 1m: compra quando preço acima VWAP, RSI sai de oversold e %K cruza %D p/ cima."""

    name = 'scalping'

    def decide(
        self, closes: list[float], has_position: bool = False, ctx: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        ctx = ctx or {}
        candles = ctx.get('candles') or []
        highs = [c['high'] for c in candles] if candles else (ctx.get('highs') or [])
        lows = [c['low'] for c in candles] if candles else (ctx.get('lows') or [])
        volumes = [c['volume'] for c in candles] if candles else (ctx.get('volumes') or [])
        closes = (closes or [c['close'] for c in candles]) if candles else closes
        if len(closes) < 2:
            return {'side': 'hold', 'confidence': 0.0, 'reason': 'series too short'}
        price = closes[-1]
        v = vwap(highs or closes, lows or closes, closes, volumes or [1.0] * len(closes))
        r = rsi(closes, 9)
        st = stochastic(closes, highs or closes, lows or closes, period=14, smooth=3)
        a = atr(highs or closes, lows or closes, closes, period=14)
        conf = 0.5
        reason = []
        if v is not None and price > v:
            conf += 0.15
            reason.append('price>VWAP')
        if r is not None and r < 35:
            conf += 0.15
            reason.append(f'RSI oversold {r:.1f}')
        if st.get('k') is not None and st.get('d') is not None and st['k'] > st['d']:
            conf += 0.1
            reason.append('K>D cross')
        if a is not None and a > 0:
            conf += 0.05
        conf = min(1.0, conf)
        if (
            not has_position
            and (v is None or price > v)
            and (r is None or r < 40)
            and (st.get('k') is not None and st.get('d') is not None and st['k'] > st['d'])
        ):
            return {
                'side': 'buy',
                'confidence': round(conf, 3),
                'reason': '; '.join(reason) or 'scalp buy',
                'price': price,
                'atr': a,
            }
        if has_position and (v is not None and price < v):
            return {
                'side': 'sell',
                'confidence': round(conf, 3),
                'reason': 'price<VWAP exit',
                'price': price,
                'atr': a,
            }
        return {
            'side': 'hold',
            'confidence': round(conf, 3),
            'reason': '; '.join(reason) or 'no setup',
            'price': price,
            'atr': a,
        }
