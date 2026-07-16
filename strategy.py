"""Estratégias (regra local, sem LLM, determinísticas).

- decide: MA-cross + filtro RSI (baseline).
- decide_combined: MA-cross + RSI + MACD + Bollinger.
"""
from indicators import ma_cross, rsi, macd, bollinger


def decide(closes: list[float], rsi_period: int = 14) -> str:
    """Retorna 'buy' | 'sell' | 'hold'.

    Regras:
    - Só considera comprar se RSI < 70 (evita topo).
    - Só considera vender se RSI > 30 (evita fundo).
    - Senão segue o cruzamento de médias.
    """
    signal = ma_cross(closes)
    r = rsi(closes, rsi_period)
    if signal == "buy" and (r is None or r < 70):
        return "buy"
    if signal == "sell" and (r is None or r > 30):
        return "sell"
    return "hold"


def decide_combined(closes: list[float], rsi_period: int = 14) -> str:
    """Estratégia combinada: MA-cross + RSI + MACD + Bollinger.

    Evita overfitting: cada filtro só RESTRINGE, nunca força trade.
    - BUY: MA-cross bullish E RSI<70 E MACD hist>0 E preço<=banda superior.
    - SELL: MA-cross bearish OU (preço>=banda superior E MACD hist<0).
    - caso contrário: HOLD.
    """
    if len(closes) < 35:  # precisamos de slow(26)+signal(9) pro MACD
        return "hold"

    cross = ma_cross(closes)
    r = rsi(closes, rsi_period)
    m = macd(closes)
    _mid, upper, lower = bollinger(closes, period=20, k=2.0)
    last = closes[-1]

    # condições de entrada
    macd_ok = m["hist"] is None or m["hist"] > 0
    not_overbought = r is None or r < 70
    not_above_band = upper is None or last <= upper

    if cross == "buy" and macd_ok and not_overbought and not_above_band:
        return "buy"

    # condições de saída
    below_band = lower is None or last >= lower
    macd_down = m["hist"] is not None and m["hist"] < 0
    if cross == "sell":
        return "sell"
    if upper is not None and last >= upper and macd_down and below_band:
        return "sell"

    return "hold"
