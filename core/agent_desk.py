"""Agent Desk — multi-agent decision loop (paper-only).

Five lightweight agents run each cycle and publish a transparent verdict:
  - MetricsAgent   : reads live market regime + volatility from cached closes.
  - NewsAgent      : aggregates crypto headlines + sentiment/impact (core.news).
  - RiskAgent      : evaluates current risk-guard thresholds (core.agent_analyzer + risk state).
  - StrategyAgent  : picks/ranks a strategy from the registry for the regime.
  - DecisionCore   : fuses the above into a single buy/sell/hold + confidence.

No LLM required (stdlib only). Designed to be augmented later by an LLM
DecisionCore. Every agent returns a structured record so the UI can render a
"chatroom" of agent reasoning.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from core import scoring
from core import news as news_mod
from core import config_loader
from core.strategy_registry import registry
from core import risk as risk_mod


@dataclass
class AgentVerdict:
    name: str
    role: str
    verdict: str  # ok | warn | alert | buy | sell | hold | neutral
    confidence: float  # 0..1
    reasoning: str
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "verdict": self.verdict,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "metrics": self.metrics,
        }


def _metrics_agent(closes: List[float]) -> AgentVerdict:
    if not closes or len(closes) < 20:
        return AgentVerdict("MetricsAgent", "market", "neutral", 0.0,
                            "Sem dados de closes suficientes.", {})
    regime = scoring.detect_regime(closes)
    vol = scoring.calculate_volatility(closes)
    rsi = scoring.rsi(closes)
    vol_state = "alta" if vol > 0.03 else "moderada" if vol > 0.015 else "baixa"
    conf = min(1.0, 0.5 + min(vol, 0.05) * 8)
    return AgentVerdict(
        "MetricsAgent", "market", "ok", conf,
        f"Regime {regime}, volatilidade {vol_state} ({vol:.2%}), RSI {rsi:.1f}.",
        {"regime": regime, "volatility": round(vol, 4), "rsi": round(rsi, 2)},
    )


def _news_agent() -> AgentVerdict:
    try:
        snap = news_mod.news_summary(limit=20)
    except Exception as e:  # never block the cycle
        return AgentVerdict("NewsAgent", "news", "neutral", 0.0,
                            f"Falha ao obter noticias: {e}", {})
    s = snap.get("sentiment", {})
    pos, neg = s.get("positive", 0), s.get("negative", 0)
    total = max(1, pos + neg + s.get("neutral", 0))
    net = (pos - neg) / total
    verdict = "ok" if net > 0.1 else "warn" if net < -0.1 else "neutral"
    conf = min(1.0, abs(net) + 0.2)
    impact = snap.get("impact_headlines", [])
    reason = f"Sentimento {pos} pos / {neg} neg / {s.get('neutral',0)} neu"
    if impact:
        reason += f"; {len(impact)} manchete(s) de alto impacto (ex: {impact[0]['title'][:50]}...)"
    return AgentVerdict("NewsAgent", "news", verdict, conf, reason,
                        {"positive": pos, "negative": neg, "neutral": s.get("neutral", 0),
                         "impact_count": len(impact)})


def _risk_agent() -> AgentVerdict:
    try:
        cfg = config_loader.load_config()
        risk_cfg = cfg.get("risk", {})
        max_dd = float(risk_cfg.get("max_drawdown_pct", 0.20))
        sl = float(risk_cfg.get("stop_loss_pct", 0.02))
    except Exception:
        max_dd, sl = 0.20, 0.02
    # Paper-only guardrail confirmed; warn if drawdown budget is loose.
    verdict = "ok" if max_dd <= 0.25 else "warn"
    conf = 0.9
    reason = (f"Risk guard ativo (paper-only). max_drawdown={max_dd:.0%}, "
              f"stop_loss={sl:.0%}. Sem exposição real.")
    return AgentVerdict("RiskAgent", "risk", verdict, conf, reason,
                        {"max_drawdown_pct": max_dd, "stop_loss_pct": sl,
                         "paper_only": True})


def _strategy_agent(closes: List[float]) -> AgentVerdict:
    try:
        strategies = registry.get_all()  # dict: id -> Strategy class
    except Exception:
        strategies = {}
    if not strategies:
        return AgentVerdict("StrategyAgent", "strategy", "neutral", 0.0,
                            "Nenhuma estrategia no registry.", {})
    regime = scoring.detect_regime(closes) if closes else "unknown"
    def _fit(item):
        sid, cls = item
        name = (cls.__name__ if hasattr(cls, "__name__") else str(sid)).lower()
        if regime in ("lateral", "volatile") and "grid" in name:
            return 1.0
        if regime in ("uptrend", "downtrend") and "llm" in name:
            return 0.9
        return 0.6
    ranked = sorted(strategies.items(), key=_fit, reverse=True)
    top_id = ranked[0][0]
    conf = _fit(ranked[0])
    return AgentVerdict(
        "StrategyAgent", "strategy", "ok", conf,
        f"Regime {regime}: melhor fit = {top_id}.",
        {"regime": regime, "top": top_id, "candidates": [s[0] for s in ranked[:3]]},
    )


def _decision_core(agents: List[AgentVerdict], closes: List[float]) -> AgentVerdict:
    # Weighted fusion: metrics + strategy push direction; news + risk gate.
    metrics = next(a for a in agents if a.name == "MetricsAgent")
    news = next(a for a in agents if a.name == "NewsAgent")
    risk = next(a for a in agents if a.name == "RiskAgent")
    strat = next(a for a in agents if a.name == "StrategyAgent")

    # Base signal from regime + strategy fit.
    regime = metrics.metrics.get("regime", "unknown")
    if regime == "uptrend":
        base = 0.7
    elif regime == "downtrend":
        base = 0.3
    else:
        base = 0.5
    base = base * 0.7 + strat.confidence * 0.3

    # News tilt.
    if news.verdict == "ok":
        base += 0.1
    elif news.verdict == "warn":
        base -= 0.15

    # Risk gate: hard block if risk warns AND drawdown budget loose.
    if risk.verdict == "warn":
        base *= 0.8

    base = max(0.0, min(1.0, base))
    if base >= 0.6:
        verdict = "buy"
    elif base <= 0.4:
        verdict = "sell"
    else:
        verdict = "hold"
    conf = round(base, 3)
    reason = (f"Fusao: regime={regime} ({metrics.confidence:.2f}), "
              f"estrategia={strat.metrics.get('top')} ({strat.confidence:.2f}), "
              f"news={news.verdict} ({news.confidence:.2f}), risk={risk.verdict}. "
              f"-> {verdict.upper()} @ {conf:.2f}")
    return AgentVerdict("DecisionCore", "fusion", verdict, conf, reason,
                        {"regime": regime, "fused_score": conf})


def run_cycle(closes: Optional[List[float]] = None) -> dict:
    """Run a full Agent Desk cycle. Returns serializable dict for the API."""
    if not closes:
        try:
            closes = scoring._cached_closes if hasattr(scoring, "_cached_closes") else []
        except Exception:
            closes = []
    t0 = time.time()
    agents = [
        _metrics_agent(closes),
        _news_agent(),
        _risk_agent(),
        _strategy_agent(closes),
    ]
    core = _decision_core(agents, closes)
    agents.append(core)
    return {
        "status": "ok",
        "cycle_id": int(t0 * 1000),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "paper_only": True,
        "agents": [a.to_dict() for a in agents],
        "decision": core.to_dict(),
    }
