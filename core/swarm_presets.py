"""Presets de times multi-agent (swarm), estilo Vibe-Trading.

Cada preset é uma função que retorna dict com:
  - name: nome exibível
  - agents: lista de nomes de agentes
  - strategy_focus: regime sugerido p/ o time
  - description: contexto narrativo

Uso:
  from core.swarm_presets import get_preset, list_presets
  team = get_preset("crypto_trading_desk")
  for v in team["agents"]:
      print(f"  - {v}")
"""
from __future__ import annotations

import logging

logger = logging.getLogger("crypto-bot")

_PRESETS: dict[str, dict] = {}


def _preset(
    name: str,
    agents: list[str],
    focus: str,
    description: str,
    behaviors: dict | None = None,
) -> dict:
    p = {
        "name": name,
        "agents": agents,
        "strategy_focus": focus,
        "description": description,
        "behaviors": behaviors or {},
    }
    _PRESETS[name] = p
    return p


# ── Presets ──────────────────────────────────────────────────────────

_crypto_trading_desk = _preset(
    "crypto_trading_desk",
    ["MetricsAgent", "NewsAgent", "RiskAgent", "StrategyAgent", "DecisionCore"],
    "crypto",
    "Time cripto completo: lê regime, volatilidade, notícias, risco, "
    "ranqueia estratégia e decide compra/venda/hold com score de confiança.",
    {"bars_lookback_h": 24, "min_confidence": 0.5},
)

_investment_committee = _preset(
    "investment_committee",
    ["MetricsAgent", "StrategyAgent", "RiskAgent", "DecisionCore"],
    "lateral",
    "Comitê de investimento para regimes laterais ou de baixa volatilidade. "
    "Foco em preservação de capital e entradas seletivas.",
    {"min_confidence": 0.65, "bars_lookback_h": 48},
)

_quant_desk = _preset(
    "quant_desk",
    ["MetricsAgent", "StrategyAgent"],
    "uptrend",
    "Desk quant focado em extrair alpha de tendência. "
    "Pula NewsAgent e RiskAgent — assume risco gerenciado externamente.",
    {"bars_lookback_h": 168, "min_confidence": 0.4},
)

_risk_committee = _preset(
    "risk_committee",
    ["RiskAgent", "MetricsAgent", "DecisionCore"],
    "downtrend",
    "Comitê de risco ativado em regimes de baixa. "
    "Prioriza stops, reduz exposição, sugere hedge / cash.",
    {"min_confidence": 0.75, "bars_lookback_h": 12, "max_exposure_pct": 0.3},
)

_scalping_desk = _preset(
    "scalping_desk",
    ["MetricsAgent", "NewsAgent", "RiskAgent", "StrategyAgent", "DecisionCore"],
    "crypto",
    "Time de scalping: janela curta (1h), notícias em tempo real, "
    "entradas e saídas rápidas. Confiança mínima reduzida p/ capturar micro-movimentos.",
    {"bars_lookback_h": 4, "min_confidence": 0.25},
)

_hedge_desk = _preset(
    "hedge_desk",
    ["RiskAgent", "MetricsAgent"],
    "lateral",
    "Desk de hedge: monitora exposição e correlação entre ativos. "
    "Apenas análise — não emite sinais de compra.",
    {"bars_lookback_h": 168, "analysis_only": True},
)


def list_presets() -> list[dict]:
    """Retorna lista de presets disponíveis."""
    return [
        {
            "name": p["name"],
            "description": p["description"],
            "strategy_focus": p["strategy_focus"],
            "agents": p["agents"],
        }
        for p in _PRESETS.values()
    ]


def get_preset(name: str) -> dict | None:
    """Retorna preset por nome, ou None."""
    return _PRESETS.get(name)
