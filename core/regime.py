import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


"""Detector de regime de mercado + seletor de estratégia.

Usa inclinação da reta de regressão linear simples (sem numpy)
para classificar o regime dos últimos N closes.

Regime:
  - uptrend:   inclinação > +threshold  -> grid_dynamic
  - downtrend: inclinação < -threshold  -> combined (ou hold)
  - lateral:   entre os dois           -> grid (estatico)

Sem look-ahead: usa apenas closes[0..t] quando chamado em backtest.
"""
import os

# percentual por candle pra classificar inclinacao
_UPTREND_THRESHOLD = 0.0005   # +0.05% por candle
_DOWNTREND_THRESHOLD = -0.0005


def _slope(closes: list[float]) -> float:
    """Inclinacao da regressao linear (pendiente) de y=closes sobre x=0..n-1.

    slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x²) - (sum(x))²)
    Normalizada por media de y para ser comparavel entre ativos.
    """
    n = len(closes)
    if n < 2:
        return 0.0
    sx = n * (n - 1) / 2          # sum(x)
    sxx = n * (n - 1) * (2*n - 1) / 6  # sum(x²)
    sy = sum(closes)
    sxy = sum(i * c for i, c in enumerate(closes))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0
    raw = (n * sxy - sx * sy) / denom
    return raw / (sy / n) if sy != 0 else raw  # normalizado pela media


def detect_regime(closes: list[float], window: int = 100) -> str:
    """Detecta regime dos últimos `window` closes.

    Retorna: "uptrend", "downtrend", ou "lateral".
    """
    logger.info("detect_regime closes=%d window=%d", len(closes), window)
    if len(closes) < 2:
        raise ValueError("closes precisa de pelo menos 2 valores")
    recent = closes[-min(window, len(closes)):]
    s = _slope(recent)
    if s > _UPTREND_THRESHOLD:
        return "uptrend"
    if s < _DOWNTREND_THRESHOLD:
        return "downtrend"
    return "lateral"


def select_strategy(closes: list[float]) -> str:
    """Seleciona a melhor estratégia para o regime atual.

    Retorna nome da estratégia para usar com run_backtest/run_cycle.
    """
    regime = detect_regime(closes)
    return {
        "uptrend": "grid_dynamic",
        "downtrend": "combined",
        "lateral": "grid",
    }[regime]
