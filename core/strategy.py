"""Estratégias (regra local, sem LLM, determinísticas).

- decide: MA-cross + filtro RSI (baseline).
- decide_combined: MA-cross + RSI + MACD + Bollinger.
- decide_grid / build_grid: grid estático em faixas (opera em lateral).
- decide_dynamic_grid / build_dynamic_grid: grid dinâmico (recentraliza).
"""

import logging

logger = logging.getLogger('crypto-bot')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


from core.indicators import bollinger, ma_cross, macd, rsi


def decide(closes: list[float], rsi_period: int = 14) -> str:
    """Retorna 'buy' | 'sell' | 'hold'.

    Regras:
    - Só considera comprar se RSI < 70 (evita topo).
    - Só considera vender se RSI > 30 (evita fundo).
    - Senão segue o cruzamento de médias.
    """
    signal = ma_cross(closes)
    r = rsi(closes, rsi_period)
    if signal == 'buy' and (r is None or r < 70):
        return 'buy'
    if signal == 'sell' and (r is None or r > 30):
        return 'sell'
    return 'hold'


def decide_combined(closes: list[float], rsi_period: int = 14) -> str:
    """Estratégia combinada: MA-cross + RSI + MACD + Bollinger.

    Evita overfitting: cada filtro só RESTRINGE, nunca força trade.
    - BUY: MA-cross bullish E RSI<70 E MACD hist>0 E preço<=banda superior.
    - SELL: MA-cross bearish OU (preço>=banda superior E MACD hist<0).
    - caso contrário: HOLD.
    """
    if len(closes) < 35:  # precisamos de slow(26)+signal(9) pro MACD
        return 'hold'

    cross = ma_cross(closes)
    r = rsi(closes, rsi_period)
    m = macd(closes)
    _mid, upper, lower = bollinger(closes, period=20, k=2.0)
    last = closes[-1]

    macd_ok = m['hist'] is None or m['hist'] > 0
    not_overbought = r is None or r < 70
    not_above_band = upper is None or last <= upper

    if cross == 'buy' and macd_ok and not_overbought and not_above_band:
        return 'buy'

    below_band = lower is None or last >= lower
    macd_down = m['hist'] is not None and m['hist'] < 0
    if cross == 'sell':
        return 'sell'
    if upper is not None and last >= upper and macd_down and below_band:
        return 'sell'

    return 'hold'


def build_grid(low: float, high: float, n: int) -> list[float]:
    """Gera n níveis de preço igualmente espaçados entre low e high."""
    if n <= 0:
        raise ValueError('n must be positive')
    if low >= high:
        raise ValueError('low must be < high')
    step = (high - low) / (n - 1)
    return [low + step * i for i in range(n)]


def decide_grid(closes: list[float], levels: list[float], has_position: bool) -> str:
    """Estratégia Grid estático (opera em lateral, sem look-ahead).

    Compra quando o preço cruza um nível para BAIXO e não tem posição.
    Vende quando cruza para CIMA e tem posição.
    Mantém HOLD caso contrário.
    """
    if len(closes) < 2 or len(levels) < 2:
        return 'hold'
    prev = closes[-2]
    last = closes[-1]

    def level_below(p: float) -> int:
        return sum(1 for lv in levels if lv <= p)

    crossed_down = level_below(prev) > level_below(last)
    crossed_up = level_below(prev) < level_below(last)

    if crossed_down and not has_position:
        return 'buy'
    if crossed_up and has_position:
        return 'sell'
    return 'hold'


def build_dynamic_grid(center: float, step: float, n: int) -> list[float]:
    """Grid dinâmico: n níveis ao redor de um centro (n ímpar -> simétrico).

    Permite recentralizar: se o preço foge do range, recalcula com novo centro.
    """
    if n <= 0 or n % 2 == 0:
        raise ValueError('n must be positive odd')
    if step <= 0:
        raise ValueError('step must be > 0')
    half = (n - 1) // 2
    return [center - step * half + step * i for i in range(n)]


def decide_dynamic_grid(closes: list[float], levels: list[float], has_position: bool) -> str:
    """Decisão no grid dinâmico (sem look-ahead).

    Compra ao cruzar nível para BAIXO (sem posição).
    Vende ao cruzar nível para CIMA (com posição).
    """
    if len(closes) < 2 or len(levels) < 2:
        return 'hold'
    prev, last = closes[-2], closes[-1]

    def below(p: float) -> int:
        return sum(1 for lv in levels if lv <= p)

    crossed_down = below(prev) > below(last)
    crossed_up = below(prev) < below(last)
    if crossed_down and not has_position:
        return 'buy'
    if crossed_up and has_position:
        return 'sell'
    return 'hold'
