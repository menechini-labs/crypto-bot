"""Testes para o módulo agent_analyzer."""

from __future__ import annotations

from core.agent_analyzer import AnalysisResult, analyze_backtest


def test_ok_assessment() -> None:
    """PnL positivo, drawdown baixo, Sharpe > 1 → ok."""
    bt = {
        "pnl_pct": 0.15,
        "max_drawdown_pct": 0.05,
        "sharpe": 1.8,
        "cagr": 0.25,
        "win_rate": 0.62,
    }
    result = analyze_backtest(bt)
    assert result.assessment == "ok"
    assert result.sharpe == 1.8


def test_warn_high_drawdown() -> None:
    """Drawdown > 10% → warn."""
    bt = {
        "pnl_pct": 0.08,
        "max_drawdown_pct": 0.15,
        "sharpe": 0.9,
    }
    result = analyze_backtest(bt)
    assert result.assessment == "warn"
    assert "ATENCAO" in result.summary


def test_alert_negative_pnl() -> None:
    """PnL negativo → alert."""
    bt = {
        "pnl_pct": -0.05,
        "max_drawdown_pct": 0.08,
        "sharpe": -0.3,
    }
    result = analyze_backtest(bt)
    assert result.assessment == "alert"
    assert "ALERTA" in result.summary


def test_alert_critical_drawdown() -> None:
    """Drawdown > 20% → alert."""
    bt = {
        "pnl_pct": 0.03,
        "max_drawdown_pct": 0.25,
        "sharpe": 0.4,
    }
    result = analyze_backtest(bt)
    assert result.assessment == "alert"
    assert "critico" in result.summary.lower()


def test_warn_low_pnl() -> None:
    """PnL < 5% → warn."""
    bt = {
        "pnl_pct": 0.02,
        "max_drawdown_pct": 0.04,
        "sharpe": 0.6,
    }
    result = analyze_backtest(bt)
    assert result.assessment == "warn"


def test_missing_fields_defaults() -> None:
    """Campos ausentes não quebram."""
    bt: dict = {}
    result = analyze_backtest(bt)
    assert isinstance(result, AnalysisResult)
    assert result.assessment in ("ok", "warn", "alert")


def test_analysis_structure() -> None:
    """to_dict() retorna as chaves esperadas."""
    bt = {"pnl_pct": 0.10, "max_drawdown_pct": 0.05, "sharpe": 1.2}
    result = analyze_backtest(bt)
    d = result.to_dict()
    for key in ("assessment", "sharpe", "cagr", "max_dd", "win_rate", "summary"):
        assert key in d
