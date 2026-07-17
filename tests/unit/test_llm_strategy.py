# tests/unit/test_llm_strategy.py
"""Testes unitarios para LLMStrategy e integracao com RiskManager."""
import os

import pytest

from core.strategy_registry.llm_strategy import LLMStrategy, _validate_signal
from core.risk import RiskManager


@pytest.fixture(autouse=True)
def _llm_env(monkeypatch):
    """Ativa LLM com credenciais fake para os testes."""
    monkeypatch.setenv("ENABLE_LLM", "1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")


def test_validate_signal_buy():
    assert _validate_signal("BUY now", has_position=False) == "buy"


def test_validate_signal_sell():
    assert _validate_signal("SELL", has_position=False) == "sell"


def test_validate_signal_hold_on_noise():
    assert _validate_signal("market looks sideways", has_position=False) == "hold"


def test_validate_signal_blocks_buy_when_in_position():
    # Nunca dobrar exposicao: buy vira hold se ja tem posicao.
    assert _validate_signal("BUY", has_position=True) == "hold"


def test_llm_disabled_falls_back_to_hold(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM", "0")
    strategy = LLMStrategy()
    assert strategy.decide([100] * 10, has_position=False) == "hold"


def test_llm_insufficient_data_falls_back(monkeypatch):
    strategy = LLMStrategy()
    assert strategy.decide([100, 101], has_position=False) == "hold"


def test_llm_request_error_falls_back_to_hold(monkeypatch):
    import core.strategy_registry.llm_strategy as mod

    def _boom(_prompt, _max_tokens=256):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(mod, "_llm_request", _boom)
    strategy = LLMStrategy()
    closes = [float(i) for i in range(100, 110)]
    assert strategy.decide(closes, has_position=False) == "hold"


def test_llm_buy_signal_passes_when_risk_ok(monkeypatch):
    import core.strategy_registry.llm_strategy as mod

    def _fake_buy(_prompt, _max_tokens=256):
        return "BUY"

    monkeypatch.setattr(mod, "_llm_request", _fake_buy)
    strategy = LLMStrategy()
    # 60 candles em clara uptrend para detectar regime + confianca alta
    closes = [float(100 + i) for i in range(60)]
    assert strategy.decide(closes, has_position=False) == "buy"


def test_llm_buy_signal_rejected_when_low_confidence(monkeypatch):
    import core.strategy_registry.llm_strategy as mod

    def _fake_buy(_prompt, _max_tokens=256):
        return "BUY"

    monkeypatch.setattr(mod, "_llm_request", _fake_buy)
    strategy = LLMStrategy()
    # 10 candles (regime unknown, RSI neutro) -> confianca baixa -> hold
    closes = [float(i) for i in range(100, 110)]
    assert strategy.decide(closes, has_position=False) == "hold"


def test_risk_manager_guardrails():
    risk = RiskManager(max_position_pct=0.5, stop_loss_pct=0.05, take_profit_pct=0.10)
    # SL atingido
    assert risk.should_stop_loss(entry=100.0, current=94.0) is True
    # TP atingido
    assert risk.should_take_profit(entry=100.0, current=111.0) is True
    # Dentro dos limites
    assert risk.should_stop_loss(entry=100.0, current=98.0) is False
    assert risk.max_notional(1000.0) == 500.0
