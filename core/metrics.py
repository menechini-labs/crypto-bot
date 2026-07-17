import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


"""Métricas de qualidade de estratégia (stdlib, sem numpy).

Recebe a curva de equity (lista de floats, ordem cronológica) e
retorna Sharpe, CAGR, max drawdown, win-rate.

Sharpe (simplificado, sem rf):
  retornos = pct de variacao entre equities consecutivos
  sharpe = mean(ret) / std(ret) * sqrt(periods_per_year)
CAGR:
  (equity_final / equity_inicial)^(1/years) - 1
  years = len/periods_per_year
"""
import math


def _returns(equity: list[float]) -> list[float]:
    out = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        if prev != 0:
            out.append((equity[i] - prev) / prev)
    return out


def compute_metrics(
    equity: list[float],
    periods_per_year: int = 365 * 24,
    wins: int = 0,
    trades: int = 0,
) -> dict:
    logger.info("compute_metrics equity_len=%d trades=%d", len(equity), trades)
    """Calcula métricas de qualidade da curva de equity.

    Retorna: sharpe, cagr, max_drawdown, win_rate.
    """
    if len(equity) < 2:
        raise ValueError("equity precisa de pelo menos 2 pontos")

    rets = _returns(equity)
    n = len(rets)
    if n == 0:
        mean_r = 0.0
        std_r = 0.0
    else:
        mean_r = sum(rets) / n
        var = sum((r - mean_r) ** 2 for r in rets) / n
        std_r = math.sqrt(var)

    if std_r > 0:
        sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)
    else:
        sharpe = 0.0

    initial = equity[0]
    final = equity[-1]
    years = len(equity) / periods_per_year if periods_per_year > 0 else 0
    if initial > 0 and years > 0:
        cagr = (final / initial) ** (1 / years) - 1
    elif initial > 0 and final >= initial:
        cagr = 0.0
    else:
        cagr = 0.0

    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)

    win_rate = (wins / trades) if trades > 0 else 0.0

    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
    }
