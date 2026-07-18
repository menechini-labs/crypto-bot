"""Indicadores técnicos (implementação mínima em stdlib).

Usados pela estratégia: SMA, RSI, EMA, MACD, Bollinger, cruzamento de médias.
"""

import logging

logger = logging.getLogger('crypto-bot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


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
        return {'macd': None, 'signal': None, 'hist': None}
    macd_line = []
    for i in range(slow, len(values) + 1):
        window = values[:i]
        f = ema(window, fast)
        s = ema(window, slow)
        assert f is not None and s is not None
        macd_line.append(f - s)
    signal_line = ema(macd_line, signal)
    if signal_line is None:
        return {'macd': macd_line[-1], 'signal': None, 'hist': None}
    hist = macd_line[-1] - signal_line
    return {'macd': macd_line[-1], 'signal': signal_line, 'hist': hist}


def bollinger(values: list[float], period: int = 20, k: float = 2.0):
    """Retorna (mid, upper, lower). None se série curta."""
    if len(values) < period:
        return (None, None, None)
    window = values[-period:]
    mid = sum(window) / period
    var = sum((x - mid) ** 2 for x in window) / period
    std = var**0.5
    return (mid, mid + k * std, mid - k * std)


def ma_cross(closes: list[float], fast: int = 5, slow: int = 20) -> str:
    """Retorna 'buy' no cruzamento ascendente, 'sell' no descendente, 'hold' caso contrário."""
    fast_now = sma(closes, fast)
    slow_now = sma(closes, slow)
    fast_prev = sma(closes[:-1], fast)
    slow_prev = sma(closes[:-1], slow)
    if fast_now is None or slow_now is None or fast_prev is None or slow_prev is None:
        return 'hold'
    if fast_prev <= slow_prev and fast_now > slow_now:
        return 'buy'
    if fast_prev >= slow_prev and fast_now < slow_now:
        return 'sell'
    return 'hold'


def vwap(
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    closes: list[float] | None = None,
    volumes: list[float] | None = None,
) -> float | None:
    highs = highs or []
    lows = lows or []
    closes = closes or []
    volumes = volumes or []
    """Volume-Weighted Average Price (intraday). Stdlib only. Retorna None se vazio."""
    n = min(len(highs), len(lows), len(closes), len(volumes))
    if n == 0:
        return None
    tp_sum = 0.0
    vol_sum = 0.0
    for i in range(n):
        typical = (highs[i] + lows[i] + closes[i]) / 3.0
        v = volumes[i]
        tp_sum += typical * v
        vol_sum += v
    if vol_sum == 0:
        return None
    return tp_sum / vol_sum


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> float | None:
    """Average True Range (Wilder smoothing). Stdlib only. None se série curta."""
    n = min(len(highs), len(lows), len(closes))
    if n < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, n):
        h, lo, pc = highs[i], lows[i], closes[i - 1]
        tr = max(h - lo, abs(h - pc), abs(lo - pc))
        trs.append(tr)
    if len(trs) < period:
        return None
    # Wilder smoothing
    atr_val = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
    return atr_val


def stochastic(
    closes: list[float], highs: list[float], lows: list[float], period: int = 14, smooth: int = 3
) -> dict:
    """Oscillator estocástico %K/%D. Retorna {k, d}. None se série curta."""
    n = min(len(closes), len(highs), len(lows))
    if n < period:
        return {'k': None, 'd': None}
    k_vals: list[float] = []
    for i in range(period - 1, n):
        window_h = highs[i - period + 1 : i + 1]
        window_l = lows[i - period + 1 : i + 1]
        hh = max(window_h)
        ll = min(window_l)
        c = closes[i]
        if hh == ll:
            k = 50.0
        else:
            k = (c - ll) / (hh - ll) * 100.0
        k_vals.append(k)
    if not k_vals:
        return {'k': None, 'd': None}
    k_now = k_vals[-1]
    if len(k_vals) < smooth:
        d_now = sum(k_vals) / len(k_vals)
    else:
        d_now = sum(k_vals[-smooth:]) / smooth
    return {'k': k_now, 'd': d_now}
