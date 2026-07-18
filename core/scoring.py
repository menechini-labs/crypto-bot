# core/scoring.py
"""Sistema de scoring para sinais de trading (stdlib-only)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SignalScore:
    """Resultado do scoring de um sinal."""

    signal: str  # "buy" | "sell" | "hold"
    confidence: float  # 0.0 - 1.0
    risk_score: float  # 0.0 - 1.0 (maior = mais seguro)
    composite: float  # weighted combination
    details: dict[str, Any]  # breakdown para auditoria


# Pesos padrao (somam 1.0)
DEFAULT_WEIGHTS = {
    'trend': 0.30,
    'momentum': 0.25,
    'volatility': 0.20,
    'risk_reward': 0.15,
    'regime': 0.10,
}

# Pesos ajustados por regime de mercado.
# Em lateral, tendencia eh ruido -> menos peso em trend, mais em vol/risk_reward.
# Em tendencia, alinhar direcao importa mais.
REGIME_WEIGHTS = {
    'uptrend': {
        'trend': 0.45,
        'momentum': 0.25,
        'volatility': 0.10,
        'risk_reward': 0.15,
        'regime': 0.05,
    },
    'downtrend': {
        'trend': 0.45,
        'momentum': 0.25,
        'volatility': 0.10,
        'risk_reward': 0.15,
        'regime': 0.05,
    },
    'lateral': {
        'trend': 0.10,
        'momentum': 0.20,
        'volatility': 0.35,
        'risk_reward': 0.25,
        'regime': 0.10,
    },
    'unknown': DEFAULT_WEIGHTS,
}


def weights_for_regime(regime: str) -> dict[str, float]:
    """Retorna pesos apropriados ao regime detectado."""
    return REGIME_WEIGHTS.get(regime, DEFAULT_WEIGHTS)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _normalize(val: float, lo: float, hi: float) -> float:
    """Normaliza valor para [0,1] dado range esperado."""
    if hi == lo:
        return 0.5
    return _clamp((val - lo) / (hi - lo))


def calculate_volatility(closes: list[float], window: int = 14) -> float:
    """ATR% aproximado via desvio padrao dos retornos."""
    if len(closes) < window + 1:
        return 0.0
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(-window, 0)]
    return statistics.stdev(rets) * 100  # %


def detect_regime(closes: list[float], fast: int = 20, slow: int = 50) -> str:
    """Classifica regime via SMA crossover."""
    if len(closes) < slow:
        return 'unknown'
    sma_fast = statistics.mean(closes[-fast:])
    sma_slow = statistics.mean(closes[-slow:])
    diff_pct = (sma_fast - sma_slow) / sma_slow * 100
    if diff_pct > 2:
        return 'uptrend'
    if diff_pct < -2:
        return 'downtrend'
    return 'lateral'


def support_resistance(closes: list[float], window: int = 20) -> tuple[float, float]:
    """Niveis simples: min/max da janela."""
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
    if avg_loss == 0:
        return 100.0  # sem perdas -> RSI maximo
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
    - closes: lista de precos de fechamento (ultimos N candles)
    - has_position: se ja esta posicionado
    - ctx: contexto extra (sl_pct, tp_pct, max_pos_pct, etc.)
    """
    ctx = ctx or {}
    regime = detect_regime(closes)
    weights = weights or weights_for_regime(regime)

    # --- Componentes individuais (0-1) ---

    # 1. Trend alignment
    trend_map = {
        ('buy', 'uptrend'): 1.0,
        ('buy', 'lateral'): 0.5,
        ('buy', 'downtrend'): 0.0,
        ('sell', 'downtrend'): 1.0,
        ('sell', 'lateral'): 0.5,
        ('sell', 'uptrend'): 0.0,
    }
    trend_score = trend_map.get((signal, regime), 0.5)

    # 2. Momentum (RSI)
    rsi_val = rsi(closes)
    if signal == 'buy':
        momentum = _normalize(rsi_val, 30, 70)  # ideal 30-70, compra <70
    elif signal == 'sell':
        momentum = _normalize(100 - rsi_val, 30, 70)
    else:
        momentum = 0.5

    # 3. Volatility penalty
    vol = calculate_volatility(closes)
    # vol > 5% penaliza, <1% premia
    volatility = _clamp(1.0 - (vol - 1.0) / 4.0)  # 1%->1.0, 5%->0.0

    # 4. Risk/Reward
    sl_pct = ctx.get('sl_pct', 0.05)
    tp_pct = ctx.get('tp_pct', 0.10)
    rr = tp_pct / sl_pct if sl_pct > 0 else 0
    risk_reward = _clamp(rr / 3.0)  # RR 3:1 = 1.0

    # 5. Regime consistency
    regime_score = 1.0 if regime != 'unknown' else 0.5

    # --- Composite ---
    components = {
        'trend': trend_score,
        'momentum': momentum,
        'volatility': volatility,
        'risk_reward': risk_reward,
        'regime': regime_score,
    }
    composite = sum(components[k] * weights[k] for k in weights)
    confidence = abs(composite - 0.5) * 2  # 0.5->0, 1.0->1, 0.0->1

    # Risk score: combina volatility + risk_reward + position guard
    position_guard = 0.0 if (has_position and signal == 'buy') else 1.0
    risk_score = _clamp((volatility + risk_reward + position_guard) / 3.0)

    # Ajuste final: hold tem confidence baixa por definicao
    if signal == 'hold':
        confidence *= 0.3
        composite = 0.5

    return SignalScore(
        signal=signal,
        confidence=round(confidence, 3),
        risk_score=round(risk_score, 3),
        composite=round(composite, 3),
        details={
            'components': {k: round(v, 3) for k, v in components.items()},
            'regime': regime,
            'rsi': round(rsi_val, 1),
            'volatility_pct': round(vol, 2),
            'risk_reward_ratio': round(rr, 2),
            'weights': weights,
        },
    )


def should_execute(score: SignalScore, min_confidence: float = 0.4, min_risk: float = 0.5) -> bool:
    """Decide se executa baseado em thresholds."""
    if score.signal == 'hold':
        return False
    return score.confidence >= min_confidence and score.risk_score >= min_risk


def explain_score(score: SignalScore) -> str:
    """Gera explicacao legivel para logs/debug."""
    d = score.details
    return (
        f'Signal: {score.signal.upper()} | '
        f'Confidence: {score.confidence:.0%} | '
        f'Risk: {score.risk_score:.0%} | '
        f'Composite: {score.composite:.2f} | '
        f'Regime: {d["regime"]} | '
        f'RSI: {d["rsi"]} | '
        f'Vol: {d["volatility_pct"]}% | '
        f'RR: {d["risk_reward_ratio"]:.1f}'
    )


# --- Template Risk Framework ---

@dataclass(frozen=True)
class TemplateRisk:
    """Risco baseado em padrões de candle/template.

    Cada atributo representa o risco (0=baixo, 1=alto) associado
    à presença de um padrão específico.
    """
    doji_risk: float = 0.0
    engulfing_risk: float = 0.0
    hammer_risk: float = 0.0
    shooting_star_risk: float = 0.0
    inside_risk: float = 0.0
    gap_risk: float = 0.0
    high_vol_risk: float = 0.0
    trend_exhaustion: float = 0.0

    def composite_risk(self) -> float:
        weights = {
            'doji_risk': 1.0,
            'engulfing_risk': 2.0,
            'hammer_risk': 1.5,
            'shooting_star_risk': 1.5,
            'inside_risk': 1.0,
            'gap_risk': 1.5,
            'high_vol_risk': 2.0,
            'trend_exhaustion': 1.0,
        }
        total_w = sum(weights.values())
        if total_w == 0:
            return 0.0
        total = (
            self.doji_risk * weights['doji_risk']
            + self.engulfing_risk * weights['engulfing_risk']
            + self.hammer_risk * weights['hammer_risk']
            + self.shooting_star_risk * weights['shooting_star_risk']
            + self.inside_risk * weights['inside_risk']
            + self.gap_risk * weights['gap_risk']
            + self.high_vol_risk * weights['high_vol_risk']
            + self.trend_exhaustion * weights['trend_exhaustion']
        )
        return total / total_w

    def to_dict(self) -> dict:
        return {
            'doji_risk': round(self.doji_risk, 3),
            'engulfing_risk': round(self.engulfing_risk, 3),
            'hammer_risk': round(self.hammer_risk, 3),
            'shooting_star_risk': round(self.shooting_star_risk, 3),
            'inside_risk': round(self.inside_risk, 3),
            'gap_risk': round(self.gap_risk, 3),
            'high_vol_risk': round(self.high_vol_risk, 3),
            'trend_exhaustion': round(self.trend_exhaustion, 3),
            'composite_risk': round(self.composite_risk(), 3),
        }


def detect_template_risk(
    opens: list[float], highs: list[float],
    lows: list[float], closes: list[float],
    period: int = 5,
) -> TemplateRisk:
    """Analisa os últimos N candles e retorna riscos baseados em padrões."""
    if len(closes) < period + 1:
        return TemplateRisk()

    o = opens[-period:]
    h = highs[-period:]
    low = lows[-period:]
    c = closes[-period:]

    doji_count = 0
    engulfing_count = 0
    hammer_count = 0
    shooting_star_count = 0
    inside_count = 0
    gap_count = 0

    for i in range(1, len(c)):
        body = abs(c[i] - o[i])
        range_candle = h[i] - low[i]

        if range_candle == 0:
            continue

        if body / range_candle < 0.1:
            doji_count += 1

        if (
            c[i] > o[i]
            and o[i] <= c[i - 1]
            and c[i] >= o[i - 1]
        ) or (
            o[i] > c[i]
            and c[i] <= o[i - 1]
            and o[i] >= c[i - 1]
        ):
            engulfing_count += 1

        shadow_lower = min(o[i], c[i]) - low[i]
        if body > 0 and shadow_lower / body >= 2 and h[i] - max(o[i], c[i]) < shadow_lower * 0.3:
            hammer_count += 1

        shadow_upper = h[i] - max(o[i], c[i])
        if body > 0 and shadow_upper / body >= 2 and min(o[i], c[i]) - low[i] < shadow_upper * 0.3:
            shooting_star_count += 1

        if h[i] <= h[i - 1] and low[i] >= low[i - 1]:
            inside_count += 1

        gap = abs(o[i] - c[i - 1]) / (max(h[i - 1] - low[i - 1], 1e-9))
        if gap > 0.5:
            gap_count += 1

    n = period - 1
    if n == 0:
        return TemplateRisk()

    vol = calculate_volatility(closes)
    high_vol_risk = 1.0 if vol > 8.0 else (vol / 8.0) if vol > 3.0 else 0.0

    trend_exhaustion = 0.0
    streak = 0
    for i in range(1, len(c)):
        if c[i] > c[i - 1]:
            streak = streak + 1 if streak > 0 else 1
        elif c[i] < c[i - 1]:
            streak = streak - 1 if streak < 0 else -1
        else:
            streak = 0
    abs_streak = abs(streak)
    if abs_streak >= 5:
        trend_exhaustion = 0.8
    elif abs_streak >= 3:
        trend_exhaustion = 0.4

    return TemplateRisk(
        doji_risk=doji_count / n,
        engulfing_risk=engulfing_count / n,
        hammer_risk=hammer_count / n,
        shooting_star_risk=shooting_star_count / n,
        inside_risk=inside_count / n,
        gap_risk=gap_count / n,
        high_vol_risk=high_vol_risk,
        trend_exhaustion=trend_exhaustion,
    )


def adjust_score_with_template(score: SignalScore, template_risk: TemplateRisk) -> SignalScore:
    """Ajusta SignalScore com base em TemplateRisk.

    Reversão (engulfing, hammer) -> +confiança.
    Indecisão (doji, inside) -> -confiança.
    """
    tr = template_risk
    adj_confidence = score.confidence
    adj_risk = score.risk_score
    adj_details = dict(score.details)

    if score.signal == 'buy':
        if tr.engulfing_risk > 0.5:
            adj_confidence = min(1.0, adj_confidence * 1.15)
        if tr.hammer_risk > 0.5:
            adj_confidence = min(1.0, adj_confidence * 1.10)
        if tr.shooting_star_risk > 0.5:
            adj_confidence *= 0.85
    elif score.signal == 'sell':
        if tr.engulfing_risk > 0.5:
            adj_confidence = min(1.0, adj_confidence * 1.15)
        if tr.shooting_star_risk > 0.5:
            adj_confidence = min(1.0, adj_confidence * 1.10)
        if tr.hammer_risk > 0.5:
            adj_confidence *= 0.85

    if tr.doji_risk > 0.5:
        adj_confidence *= 0.9
        adj_risk *= 0.9
    if tr.inside_risk > 0.5:
        adj_confidence *= 0.9
    if tr.gap_risk > 0.5:
        adj_confidence *= 0.85

    adj_confidence = max(0.0, min(1.0, adj_confidence))
    adj_risk = max(0.0, min(1.0, adj_risk))

    adj_details['template_risk'] = tr.to_dict()
    adj_details['template_adjusted'] = True

    return SignalScore(
        signal=score.signal,
        confidence=round(adj_confidence, 3),
        risk_score=round(adj_risk, 3),
        composite=round(score.composite, 3),
        details=adj_details,
    )
