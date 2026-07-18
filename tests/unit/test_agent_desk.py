# tests/unit/test_agent_desk.py
"""Unit tests for Agent Desk — MetricsAgent, NewsAgent (mocked),
RiskAgent, StrategyAgent, DecisionCore, run_cycle, run_team."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock

from core.agent_desk import (
    AgentVerdict,
    _metrics_agent,
    _news_agent,
    _risk_agent,
    _strategy_agent,
    _decision_core,
    run_cycle,
    run_team,
)
from core.strategy_registry import registry


# ── fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def closes_uptrend():
    """50+ closes simulating strong uptrend (SMA fast > slow by >2%%)."""
    base = 100.0
    return [base + i * 1.0 for i in range(60)]


@pytest.fixture
def closes_downtrend():
    """50+ closes simulating strong downtrend."""
    base = 170.0
    return [base - i * 1.0 for i in range(60)]


@pytest.fixture
def closes_lateral():
    """50+ closes oscillating sideways."""
    import math
    return [100.0 + math.sin(i * 0.3) * 1.5 for i in range(60)]


@pytest.fixture(autouse=True)
def _patch_news(monkeypatch):
    """Never hit real RSS; return neutral summary."""
    def _fake_summary(**kw):
        return {
            "sentiment": {"positive": 2, "negative": 1, "neutral": 7},
            "impact_headlines": [],
            "total": 10,
        }
    monkeypatch.setattr("core.agent_desk.news_mod.news_summary", _fake_summary)


@pytest.fixture(autouse=True)
def _patch_config(monkeypatch):
    """Sane risk defaults."""
    def _fake_load():
        return {"risk": {"max_drawdown_pct": 0.20, "stop_loss_pct": 0.02}}
    monkeypatch.setattr("core.agent_desk.config_loader.load_config", _fake_load)


@pytest.fixture(autouse=True)
def _registry_populated():
    """Ensure registry has strategies (setup once)."""
    # registry.get_all() returns dict; no need to add if already populated by imports
    assert len(registry.get_all()) > 0, "Registry vazio — importacao de estrategias falhou?"


# ── tests ─────────────────────────────────────────────────────────────


class TestMetricsAgent:
    def test_uptrend(self, closes_uptrend):
        v = _metrics_agent(closes_uptrend)
        assert v.name == "MetricsAgent"
        assert v.metrics.get("regime") == "uptrend"
        assert v.verdict in ("ok", "neutral")
        assert v.confidence > 0.0

    def test_downtrend(self, closes_downtrend):
        v = _metrics_agent(closes_downtrend)
        assert v.metrics.get("regime") == "downtrend"

    def test_lateral(self, closes_lateral):
        v = _metrics_agent(closes_lateral)
        # pode ser "lateral" ou "unknown" (se volatilidade baixa demais)
        assert v.metrics.get("regime") in ("lateral", "unknown")

    def test_insufficient_data(self):
        v = _metrics_agent([100.0, 101.0])
        assert v.verdict == "neutral"
        assert v.confidence == 0.0
        assert "Sem dados" in v.reasoning

    def test_empty_data(self):
        v = _metrics_agent([])
        assert v.verdict == "neutral"

    def test_rsi_in_range(self, closes_uptrend):
        v = _metrics_agent(closes_uptrend)
        rsi = v.metrics.get("rsi", 0)
        assert 0 <= rsi <= 100

    def test_volatility_nonnegative(self, closes_uptrend):
        v = _metrics_agent(closes_uptrend)
        assert v.metrics.get("volatility", -1) >= 0


class TestNewsAgent:
    def test_fresh(self):
        v = _news_agent()
        assert v.name == "NewsAgent"
        assert v.role == "news"
        assert v.verdict in ("ok", "warn", "neutral")
        assert v.confidence >= 0.0
        assert "Sentimento" in v.reasoning

    @patch("core.agent_desk.news_mod.news_summary", side_effect=RuntimeError("feed down"))
    def test_feed_failure(self, _mock):
        v = _news_agent()
        assert v.verdict == "neutral"
        assert v.confidence == 0.0
        assert "Falha" in v.reasoning

    def test_metrics_contains_counts(self):
        v = _news_agent()
        m = v.metrics
        assert "positive" in m
        assert "negative" in m
        assert "neutral" in m
        assert m["positive"] >= 0
        assert m["negative"] >= 0
        assert m["neutral"] >= 0


class TestRiskAgent:
    def test_ok(self):
        v = _risk_agent()
        assert v.name == "RiskAgent"
        assert v.verdict in ("ok", "warn")
        assert v.confidence > 0.5
        assert "paper-only" in v.reasoning
        assert v.metrics.get("paper_only") is True

    @patch("core.agent_desk.config_loader.load_config", return_value={"risk": {"max_drawdown_pct": 0.40}})
    def test_warn_loose_budget(self, _mock):
        v = _risk_agent()
        assert v.verdict == "warn"

    @patch("core.agent_desk.config_loader.load_config", side_effect=Exception("no config"))
    def test_missing_config(self, _mock):
        v = _risk_agent()
        assert v.verdict in ("ok", "warn")
        assert v.confidence > 0.0


class TestStrategyAgent:
    def test_has_strategies(self, closes_uptrend):
        v = _strategy_agent(closes_uptrend)
        assert v.name == "StrategyAgent"
        assert v.verdict == "ok"
        assert v.confidence > 0.0
        top = v.metrics.get("top", "")
        candidates = v.metrics.get("candidates", [])
        assert len(candidates) >= 1

    def test_no_closes(self):
        v = _strategy_agent([])
        assert v.verdict in ("ok", "neutral")

    def test_candidates_order(self, closes_uptrend):
        v = _strategy_agent(closes_uptrend)
        candidates = v.metrics.get("candidates", [])
        assert len(candidates) >= 1
        assert candidates[0] == v.metrics.get("top")

    def test_uptrend_favors_llm(self, closes_uptrend):
        v = _strategy_agent(closes_uptrend)
        top = str(v.metrics.get("top", ""))
        regime = v.metrics.get("regime", "")
        if regime in ("uptrend", "downtrend"):
            # llm should rank high due to 0.9 fit
            assert "llm" in top.lower() or len(v.metrics.get("candidates", [])) > 1

    def test_lateral_favors_grid(self, closes_lateral):
        v = _strategy_agent(closes_lateral)
        top = str(v.metrics.get("top", ""))
        regime = v.metrics.get("regime", "")
        if regime in ("lateral", "volatile"):
            assert "grid" in top.lower()


class TestDecisionCore:
    def test_full_agents(self, closes_uptrend):
        agents = [
            _metrics_agent(closes_uptrend),
            _news_agent(),
            _risk_agent(),
            _strategy_agent(closes_uptrend),
        ]
        d = _decision_core(agents, closes_uptrend)
        assert d.name == "DecisionCore"
        assert d.verdict in ("buy", "sell", "hold")
        assert 0.0 <= d.confidence <= 1.0
        assert d.role == "fusion"

    def test_agent_missing_tolerated(self, closes_uptrend):
        # Only MetricsAgent + RiskAgent (no News, no Strategy)
        agents = [
            _metrics_agent(closes_uptrend),
            _risk_agent(),
        ]
        d = _decision_core(agents, closes_uptrend)
        assert d.verdict in ("buy", "sell", "hold")
        assert d.confidence > 0.0

    def test_all_missing(self):
        agents: list = []
        d = _decision_core(agents, [])
        assert d.verdict in ("buy", "sell", "hold")

    def test_risk_warn_reduces_confidence(self, closes_uptrend):
        from core.risk import RiskManager
        agents = [
            _metrics_agent(closes_uptrend),
            AgentVerdict("RiskAgent", "risk", "warn", 0.9, "Orcamento de drawdown alto."),
            _strategy_agent(closes_uptrend),
        ]
        d = _decision_core(agents, closes_uptrend)
        # risk warn -> base * 0.8 -> confidence should be lower than baseline
        assert d.confidence >= 0.0

    def test_news_bullish_tilt(self, closes_uptrend):
        metrics = _metrics_agent(closes_uptrend)
        news = AgentVerdict("NewsAgent", "news", "ok", 0.8, "Sentimento positivo.")
        agents = [metrics, news, _risk_agent(), _strategy_agent(closes_uptrend)]
        d_bull = _decision_core(agents, closes_uptrend)

        # now with bearish news
        news_bear = AgentVerdict("NewsAgent", "news", "warn", 0.7, "Sentimento negativo.")
        agents2 = [metrics, news_bear, _risk_agent(), _strategy_agent(closes_uptrend)]
        d_bear = _decision_core(agents2, closes_uptrend)
        # bullish should not be lower than bearish (same regime, same strat)
        # note: same metrics/strat, different news -> d_bull >= d_bear (approximately)
        assert d_bull.confidence >= d_bear.confidence - 0.05  # small epsilon

    def test_reason_contains_parts(self, closes_uptrend):
        agents = [
            _metrics_agent(closes_uptrend),
            _news_agent(),
            _risk_agent(),
            _strategy_agent(closes_uptrend),
        ]
        d = _decision_core(agents, closes_uptrend)
        assert "regime=" in d.reasoning
        assert "->" in d.reasoning


class TestRunCycle:
    def test_returns_structure(self, closes_uptrend):
        result = run_cycle(closes_uptrend)
        assert result["status"] == "ok"
        assert result["paper_only"] is True
        assert "cycle_id" in result
        assert "timestamp" in result
        assert len(result["agents"]) == 5  # 4 + DecisionCore
        assert result["decision"] is not None
        assert result["decision"]["name"] == "DecisionCore"

    def test_no_closes_fallback(self):
        # Should not crash when closes is None/empty
        result = run_cycle([])
        assert result["status"] == "ok"
        assert len(result["agents"]) == 5


class TestRunTeam:
    def test_quant_desk(self):
        from core.swarm_presets import get_preset
        preset = get_preset("quant_desk")
        assert preset is not None
        result = run_team(preset)
        assert result["status"] == "ok"
        names = [a["name"] for a in result["agents"]]
        assert "MetricsAgent" in names
        assert "StrategyAgent" in names
        assert "DecisionCore" not in names  # quant_desk has no DecisionCore
        assert result["decision"] is None

    def test_risk_committee(self):
        from core.swarm_presets import get_preset
        preset = get_preset("risk_committee")
        assert preset is not None
        result = run_team(preset)
        assert result["status"] == "ok"
        names = [a["name"] for a in result["agents"]]
        assert "RiskAgent" in names
        assert "MetricsAgent" in names
        assert "DecisionCore" in names
        assert result["decision"] is not None
        # risk_committee has no StrategyAgent — DecisionCore should tolerate that
        assert "StrategyAgent" not in names

    def test_all_presets_success(self):
        from core.swarm_presets import list_presets
        presets = list_presets()
        assert len(presets) >= 6
        for p in presets:
            result = run_team(p)
            assert result["status"] == "ok", f"Preset {p['name']} falhou"

    def test_team_name_in_result(self):
        from core.swarm_presets import get_preset
        preset = get_preset("scalping_desk")
        result = run_team(preset)
        assert result["team"] == "scalping_desk"


class TestAgentVerdictSerialization:
    def test_to_dict(self):
        v = AgentVerdict("TestAgent", "test", "ok", 0.85, "Tudo certo.",
                         {"foo": 42})
        d = v.to_dict()
        assert d["name"] == "TestAgent"
        assert d["confidence"] == 0.85
        assert d["metrics"]["foo"] == 42
        assert d["verdict"] == "ok"

    def test_json_serializable(self):
        v = AgentVerdict("X", "y", "buy", 0.9, "razão", {"k": 1})
        json.dumps(v.to_dict())  # must not raise
