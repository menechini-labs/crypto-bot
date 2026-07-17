"""Testes do ReflectionAgent (core/reflection.py)."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from core.reflection import (
    reflect_trades,
    save_reflection,
    load_reflections,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _trade(
    side: str,
    entry: float = 100.0,
    exit_: float = 105.0,
    pnl: float = 5.0,
    pnl_pct: float = 0.05,
    duration_min: int = 120,
) -> dict:
    return {
        "side": side,
        "entry_price": entry,
        "exit_price": exit_,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "duration_min": duration_min,
    }


def _losing_trade(
    side: str = "buy",
    entry: float = 100.0,
    exit_: float = 95.0,
    pnl: float = -5.0,
    pnl_pct: float = -0.05,
    duration_min: int = 180,
) -> dict:
    return _trade(side, entry, exit_, pnl, pnl_pct, duration_min)


WINNERS = [
    _trade("buy", 100, 110, 10.0, 0.10, 120),
    _trade("buy", 105, 115, 10.0, 0.095, 90),
    _trade("buy", 98, 108, 10.0, 0.102, 150),
    _trade("sell", 110, 100, 10.0, 0.09, 60),
    _trade("sell", 120, 105, 15.0, 0.125, 75),
    _trade("sell", 95, 85, 10.0, 0.105, 80),
]

LOSERS = [
    _losing_trade("buy", 100, 92, -8.0, -0.08, 240),
    _losing_trade("buy", 105, 97, -8.0, -0.076, 300),
    _losing_trade("sell", 110, 118, -8.0, -0.073, 200),
    _losing_trade("sell", 95, 104, -9.0, -0.095, 350),
]

MIXED_TRADES = WINNERS[:3] + LOSERS[:2] + WINNERS[3:]

STREAK_LOSERS = [_losing_trade() for _ in range(7)]


# ---------------------------------------------------------------------------
# reflect_trades
# ---------------------------------------------------------------------------


class TestReflectTrades:
    def test_empty_trades(self) -> None:
        result = reflect_trades([])
        assert result["total_trades"] == 0
        assert result["insights"] == []
        assert result["metrics"] == {}

    def test_all_winners(self) -> None:
        result = reflect_trades(WINNERS)
        assert result["total_trades"] == 6
        assert result["metrics"]["win_rate"] == 1.0
        assert result["metrics"]["total_pnl"] == 65.0
        assert result["metrics"]["max_consecutive_losses"] == 0

    def test_all_losers(self) -> None:
        result = reflect_trades(LOSERS)
        assert result["total_trades"] == 4
        assert result["metrics"]["win_rate"] == 0.0
        assert result["metrics"]["total_pnl"] < 0
        insight_texts = " ".join(result["insights"]).lower()
        assert "baixo" in insight_texts or "não lucrativa" in insight_texts

    def test_mixed_trades(self) -> None:
        result = reflect_trades(MIXED_TRADES)
        assert result["total_trades"] == 8
        wr = result["metrics"]["win_rate"]
        assert 0.5 <= wr <= 0.8  # 5 winners out of 8 = 0.625

    def test_metric_values(self) -> None:
        """Verifica campos numericos do metrics."""
        result = reflect_trades(WINNERS)
        m = result["metrics"]
        assert m["avg_winner_pct"] > 0
        assert m["avg_loser_pct"] == 0  # sem losers
        assert m["profit_factor"] == float("inf")  # divisao por zero
        assert m["buy_win_rate"] == 1.0
        assert m["sell_win_rate"] == 1.0
        assert m["avg_duration_min"] > 0
        assert m["median_duration_min"] > 0

    def test_max_consecutive_losses(self) -> None:
        result = reflect_trades(STREAK_LOSERS)
        assert result["metrics"]["max_consecutive_losses"] == 7
        insight_texts = " ".join(result["insights"]).lower()
        assert "7" in insight_texts
        assert "perdas consecutivas" in insight_texts

    def test_pattern_recent_decline(self) -> None:
        """Ultimos 3 trades perdedores consecutivos geram recent_decline."""
        trades = WINNERS[:2] + STREAK_LOSERS[:4]
        result = reflect_trades(trades)
        pattern_types = [p["type"] for p in result["patterns"]]
        assert "recent_decline" in pattern_types

    def test_pattern_loser_holds_too_long(self) -> None:
        """Perdedores duram muito mais que ganhadores."""
        trades = [
            _trade("buy", 100, 110, 10, 0.10, 30),  # winner curto
            _trade("buy", 100, 110, 10, 0.10, 40),
            _losing_trade(duration_min=300),  # loser longo
            _losing_trade(duration_min=400),
        ]
        result = reflect_trades(trades)
        pattern_types = [p["type"] for p in result["patterns"]]
        assert "loser_holds_too_long" in pattern_types

    def test_pattern_concentrated_gains(self) -> None:
        """Top 3 trades > 50% do PnL total."""
        trades = WINNERS[:5] + [_losing_trade(pnl=-2.0)]
        result = reflect_trades(trades)
        pattern_types = [p["type"] for p in result["patterns"]]
        assert "concentrated_gains" in pattern_types

    def test_regime_parameter(self) -> None:
        result = reflect_trades(WINNERS, regime="uptrend", strategy="grid_dynamic")
        assert result["regime"] == "uptrend"
        assert result["strategy"] == "grid_dynamic"

    def test_recommendations_generated(self) -> None:
        result = reflect_trades(STREAK_LOSERS)
        assert len(result["recommendations"]) >= 1

    def test_regime_weakness_pattern(self) -> None:
        """Trades com regime downtrend com perda geram pattern."""
        trades = [
            {**_losing_trade(), "regime": "downtrend"},
            {**_losing_trade(), "regime": "downtrend"},
            {**_losing_trade(), "regime": "downtrend"},
        ]
        result = reflect_trades(trades, regime="downtrend")
        pattern_types = [p["type"] for p in result["patterns"]]
        assert "regime_weakness" in pattern_types


# ---------------------------------------------------------------------------
# save_reflection / load_reflections
# ---------------------------------------------------------------------------


class TestReflectionPersistence:
    def setup_method(self) -> None:
        self.tmp = tempfile.mktemp(suffix=".json")

    def teardown_method(self) -> None:
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_save_creates_file(self) -> None:
        """Salva em data/reflections.json, garante que arquivo existe."""
        with patch("core.reflection._REFLECTIONS_FILE", self.tmp):
            result = reflect_trades(WINNERS)
            path = save_reflection(result)
            assert os.path.exists(path)
            assert path == self.tmp

    def test_save_and_load(self) -> None:
        # Patch para usar arquivo temporario
        with patch("core.reflection._REFLECTIONS_FILE", self.tmp):
            r1 = reflect_trades(WINNERS[:2])
            save_reflection(r1)
            loaded = load_reflections(limit=5)
            assert len(loaded) == 1
            assert loaded[0]["total_trades"] == 2

    def test_load_empty_no_file(self) -> None:
        with patch("core.reflection._REFLECTIONS_FILE", self.tmp):
            assert load_reflections() == []

    def test_preserves_multiple_reflections(self) -> None:
        with patch("core.reflection._REFLECTIONS_FILE", self.tmp):
            save_reflection(reflect_trades(WINNERS[:2]))
            save_reflection(reflect_trades(LOSERS[:1]))
            loaded = load_reflections(limit=5)
            assert len(loaded) == 2
            assert loaded[-1]["total_trades"] == 1  # ultimo salvo

    def test_limit_pagination(self) -> None:
        with patch("core.reflection._REFLECTIONS_FILE", self.tmp):
            for i in range(10):
                save_reflection(reflect_trades(WINNERS[:1]))
            loaded = load_reflections(limit=3)
            assert len(loaded) == 3

    def test_history_trimming(self) -> None:
        """Nao excede 50 entradas depois de muitas saves."""
        with patch("core.reflection._REFLECTIONS_FILE", self.tmp):
            for _ in range(55):
                save_reflection(reflect_trades(WINNERS[:1]))
            with open(self.tmp) as f:
                data = json.load(f)
            assert len(data) == 50
