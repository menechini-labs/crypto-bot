"""Estratégias adicionais baseadas em indicadores.

Registradas automaticamente via decorator @register.
"""

from .base import BaseStrategy
from .registry import register
from ..indicators import sma, ema, rsi, macd, bollinger, ma_cross


@register("ma_cross")
class MaCrossStrategy(BaseStrategy):
    """Cross de médias: compra quando fast EMA cruza acima slow SMA."""

    def decide(self, closes: list[float], has_position: bool, ctx=None) -> str:
        sig = ma_cross(closes, fast=5, slow=20)
        if sig == "buy":
            return "buy"
        elif sig == "sell":
            return "sell"
        return "hold"


@register("rsi_oversold")
class RsiOversoldStrategy(BaseStrategy):
    """Compra em oversold (RSI < 30), vende em overbought (RSI > 70)."""

    def decide(self, closes: list[float], has_position: bool, ctx=None) -> str:
        r = rsi(closes, 14)
        if r is None:
            return "hold"
        if r < 30 and not has_position:
            return "buy"
        if r > 70 and has_position:
            return "sell"
        return "hold"


@register("bollinger_reversal")
class BollingerReversalStrategy(BaseStrategy):
    """Reversão à média: compra perto banda inferior, vende perto banda superior."""

    def decide(self, closes: list[float], has_position: bool, ctx=None) -> str:
        bb = bollinger(closes)
        if bb is None or bb[0] is None:
            return "hold"
        mid, upper, lower = bb
        price = closes[-1]
        if price <= lower and not has_position:
            return "buy"
        if price >= upper and has_position:
            return "sell"
        return "hold"


@register("trend_follow")
class TrendFollowStrategy(BaseStrategy):
    """Follow the trend: EMA curta > EMA longa → compra, contrário vende."""

    def decide(self, closes: list[float], has_position: bool, ctx=None) -> str:
        e = ema(closes, 9)
        s = sma(closes, 50)
        if e is None or s is None:
            return "hold"
        if e > s and not has_position:
            return "buy"
        if e < s and has_position:
            return "sell"
        return "hold"


@register("macd_signal")
class MacdSignalStrategy(BaseStrategy):
    """MACD histograma: positivo → compra, negativo → vende."""

    def decide(self, closes: list[float], has_position: bool, ctx=None) -> str:
        m = macd(closes)
        if m is None or m.get("hist") is None:
            return "hold"
        hist = m.get("hist", 0)
        if hist > 0 and not has_position:
            return "buy"
        if hist < 0 and has_position:
            return "sell"
        return "hold"
