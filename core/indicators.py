"""Indicadores técnicos (implementação mínima em stdlib).

Usados pela estratégia: SMA, RSI, EMA, MACD, Bollinger, cruzamento de médias.
"""


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def ema(values: list[float], period: int) -> float | None:
    """Média móvel exponencial (último valor). Retorna None se insuficiente."""
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema_prev = sum(values[:period]) / period
    for v in values[period:]:
        ema_prev = v * k + ema_prev * (1 - k)
    return ema_prev


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Retorna {macd, signal, hist}. None se série curta demais."""
    if len(values) < slow + signal:
        return {"macd": None, "signal": None, "hist": None}
    macd_line = []
    for i in range(slow, len(values) + 1):
        window = values[:i]
        f = ema(window, fast)
        s = ema(window, slow)
        macd_line.append(f - s)
    signal_line = ema(macd_line, signal)
    if signal_line is None:
        return {"macd": macd_line[-1], "signal": None, "hist": None}
    hist = macd_line[-1] - signal_line
    return {"macd": macd_line[-1], "signal": signal_line, "hist": hist}


def bollinger(values: list[float], period: int = 20, k: float = 2.0):
    """Retorna (mid, upper, lower). None se série curta."""
    if len(values) < period:
        return (None, None, None)
    window = values[-period:]
    mid = sum(window) / period
    var = sum((x - mid) ** 2 for x in window) / period
    std = var ** 0.5
    return (mid, mid + k * std, mid - k * std)


def ma_cross(closes: list[float], fast: int = 5, slow: int = 20) -> str:
    """Retorna 'buy' no cruzamento ascendente, 'sell' no descendente, 'hold' caso contrário."""
    fast_now = sma(closes, fast)
    slow_now = sma(closes, slow)
    fast_prev = sma(closes[:-1], fast)
    slow_prev = sma(closes[:-1], slow)
    if None in (fast_now, slow_now, fast_prev, slow_prev):
        return "hold"
    if fast_prev <= slow_prev and fast_now > slow_now:
        return "buy"
    if fast_prev >= slow_prev and fast_now < slow_now:
        return "sell"
    return "hold"
