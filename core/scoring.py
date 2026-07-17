# core/scoring.py
"""Sistema de scoring para sinais de trading (stdlib-only)."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SignalScore:
    """Resultado do scoring de um sinal."""
    signal: str              # "buy" | "sell" | "hold"
    confidence: float        # 0.0 - 1.0
    risk_score: float        # 0.0 - 1.0 (maior = mais seguro)
    composite: float         # weighted combination
    details: dict[str, Any]  # breakdown para auditoria


# Pesos padrão (somam 1.0)
DEFAULT_WEIGHTS = {
    "trend": 0.30,
    "momentum": 0.25,
    "volatility": 0.20,
    "risk_reward": 0.15,
    "regime": 0.10,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _normalize(val: float, lo: float, hi: float) -> float:
    """Normaliza valor para [0,1] dado range esperado."""
    if hi == lo:
        return 0.5
    return _clamp((val - lo) / (hi - lo))


def calculate_volatility(closes: list[float], window: int = 14) -> float:
    """ATR% aproximado via desvio padrão dos retornos."""
    if len(closes) < window + 1:
        return 0.0
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(-window, 0)]
    return statistics.stdev(rets) * 100  # %


def detect_regime(closes: list[float], fast: int = 20, slow: int = 50) -> str:
    """Classifica regime via SMA crossover."""
    if len(closes) < slow:
        return "unknown"
    sma_fast = statistics.mean(closes[-fast:])
    sma_slow = statistics.mean(closes[-slow:])
    diff_pct = (sma_fast - sma_slow) / sma_slow * 100
    if diff_pct > 2:
        return "uptrend"
    if diff_pct < -2:
        return "downtrend"
    return "lateral"


def support_resistance(closes: list[float], window: int = 20) -> tuple[float, float]:
    """Níveis simples: min/max da janela."""
    recent = closes[-window:]
    return min(recent), max(recent)


def rsi(closes: list[float], period: int = 14) -> float:
    """RSI simplificado."""
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-diff)
    avg_gain = statistics.mean(gains) if gains else 0.0
    avg_loss = statistics.mean(losses) if losses else 1e-9
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def score_signal(
    closes: list[float],
    signal: str,
    has_position: bool,
    ctx: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> SignalScore:
    """
    Calcula score composto para um sinal.
    - signal: "buy" | "sell" | "hold" (do LLM ou strategy)
    - closes: lista de preços de fechamento (últimos N candles)
    - has_position: se já está posicionado
    - ctx: contexto extra (sl_pct, tp_pct, max_pos_pct, etc.)
    """
    ctx = ctx or {}
    w = weights or DEFAULT_WEIGHTS

    # --- Componentes individuais (0-1) ---

    # 1. Trend alignment
    regime = detect_regime(closes)
    trend_map = {
        ("buy", "uptrend"): 1.0,
        ("buy", "lateral"): 0.5,
        ("buy", "downtrend"): 0.0,
        ("sell", "downtrend"): 1.0,
        ("sell", "lateral"): 0.5,
        ("sell", "uptrend"): 0.0,
        ("hold", _): 0.5,
    }
    trend_score = trend_map.get((signal, regime), 0.5)

    # 2. Momentum (RSI)
    rsi_val = rsi(closes)
    if signal == "buy":
        momentum = _normalize(rsi_val, 30, 70)  # ideal 30-70, compra <70
    elif signal == "sell":
        momentum = _normalize(100 - rsi_val, 30, 70)
    else:
        momentum = 0.5

    # 3. Volatility penalty
    vol = calculate_volatility(closes)
    # vol > 5% penaliza, <1% premia
    volatility = _clamp(1.0 - (vol - 1.0) / 4.0)  # 1%->1.0, 5%->0.0

    # 4. Risk/Reward
    sl_pct = ctx.get("sl_pct", 0.05)
    tp_pct = ctx.get("tp_pct", 0.10)
    rr = tp_pct / sl_pct if sl_pct > 0 else 0
    risk_reward = _clamp(rr / 3.0)  # RR 3:1 = 1.0

    # 5. Regime consistency (already in trend, but extra)
    regime_score = 1.0 if regime != "unknown" else 0.5

    # --- Composite ---
    components = {
        "trend": trend_score,
        "momentum": momentum,
        "volatility": volatility,
        "risk_reward": risk_reward,
        "regime": regime_score,
    }
    composite = sum(components[k] * w[k] for k in w)

    # Confidence: quão forte o sinal (distância de 0.5)
    confidence = abs(composite - 0.5) * 2  # 0.5->0, 1.0->1, 0.0->1

    # Risk score: combina volatility + risk_reward + position guard
    position_guard = 0.0 if (has_position and signal == "buy") else 1.0
    risk_score = _clamp((volatility + risk_reward + position_guard) / 3.0)

    # Ajuste final: hold tem confidence baixa por definição
    if signal == "hold":
        confidence *= 0.3
        composite = 0.5

    return SignalScore(
        signal=signal,
        confidence=round(confidence, 3),
        risk_score=round(risk_score, 3),
        composite=round(composite, 3),
        details={
            "components": {k: round(v, 3) for k, v in components.items()},
            "regime": regime,
            "rsi": round(rsi_val, 1),
            "volatility_pct": round(vol, 2),
            "risk_reward_ratio": round(rr, 2),
            "weights": w,
        },
    )


# --- Helper para integração direta no LLM Strategy ---

def should_execute(score: SignalScore, min_confidence: float = 0.4, min_risk: float = 0.5) -> bool:
    """Decide se executa baseado em thresholds."""
    if score.signal == "hold":
        return False
    return score.confidence >= min_confidence and score.risk_score >= min_risk


def explain_score(score: SignalScore) -> str:
    """Gera explicação legível para logs/debug."""
    d = score.details
    return (
        f"Signal: {score.signal.upper()} | "
        f"Confidence: {score.confidence:.0%} | "
        f"Risk: {score.risk_score:.0%} | "
        f"Composite: {score.composite:.2f} | "
        f"Regime: {d['regime']} | "
        f"RSI: {d['rsi']} | "
        f"Vol: {d['volatility_pct']}% | "
        f"RR: {d['risk_reward_ratio']:.1f}"
    )