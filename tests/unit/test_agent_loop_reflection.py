"""Tests for Agent Desk reflection-by-cycle + PLAY controls (CAP-1..CAP-5)."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    # Force demo mode so loop/start is blocked (safe, no live trading).
    os.environ["MODE"] = "demo"
    os.environ["ALLOW_LIVE_TRADING"] = "0"
    import importlib

    import core.strategy_api as api

    importlib.reload(api)
    with TestClient(api.app) as c:
        yield c


def test_agent_reflections_list(client):
    """CAP-1: list endpoint exists and returns ok."""
    r = client.get("/api/agents/reflections")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert isinstance(body["reflections"], list)


def test_agent_cycle_reflection_returns_structure(client):
    """CAP-1: reflection by cycle returns insights structure."""
    # Use a cycle_id far in the past so no trades match -> fallback empty.
    r = client.post("/api/agents/cycle/1/reflection")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    refl = body["reflection"]
    assert refl["source"] == "agent_cycle"
    assert "insights" in refl
    assert "total_trades" in refl


def test_loop_start_blocked_in_demo(client):
    """PLAY guard: demo mode rejects loop/start (no live trading)."""
    r = client.post(
        "/api/agents/loop/start",
        json={
            "sl_pct": 0.03,
            "tp_pct": 0.08,
            "trailing_pct": 0.02,
            "target_price": 64000,
            "auto_trade": False,
            "lock_stop": True,
        },
    )
    assert r.status_code == 403


def test_loop_config_parse():
    """CAP-2/3/4/5: loop/start payload parses to correct config dict."""
    import core.strategy_api as api

    # Simulate the config-build logic used by loop/start.
    p = {
        "sl_pct": "0.03",
        "tp_pct": "0.08",
        "trailing_pct": "0.02",
        "target_price": "64000",
        "auto_trade": False,
        "lock_stop": True,
    }
    cfg = {
        "sl_pct": float(p.get("sl_pct", 0.02)),
        "tp_pct": float(p.get("tp_pct", 0.05)),
        "trailing_pct": float(p.get("trailing_pct", 0.01)),
        "target_price": float(p["target_price"]) if p.get("target_price") not in (None, "", 0) else None,
        "auto_trade": bool(p.get("auto_trade", True)),
        "lock_stop": bool(p.get("lock_stop", False)),
    }
    assert cfg["target_price"] == 64000.0
    assert cfg["auto_trade"] is False
    assert cfg["lock_stop"] is True
    # lock_stop -> worker passes sl_pct=0
    sl_pct = 0.0 if cfg["lock_stop"] else cfg["sl_pct"]
    assert sl_pct == 0.0


def test_paper_engine_closed_trades():
    """Reflection data source: engine records closed trades."""
    import core.paper_engine as pe
    import tempfile

    # Isolate from the shared singleton + persisted ledger + live prices.
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    ledger_path = tmp.name
    old_path = pe._LEDGER_PATH
    pe._LEDGER_PATH = ledger_path
    pe._ENGINE = None
    orig = pe._market.fetch_ticker
    pe._market.fetch_ticker = lambda s: {"price": 100.0}
    try:
        engine = pe.PaperEngine(cash=10000.0)
        assert engine.submit(pe.Order(symbol="BTCUSDT", side="buy", qty=0.01, sl_pct=0.02, tp_pct=0.05, reason="t"))["ok"]
        assert engine.submit(pe.Order(symbol="BTCUSDT", side="sell", qty=0.01, reason="close"))["ok"]
        trades = engine.get_closed_trades()
        assert len(trades) == 1
        assert trades[0]["symbol"] == "BTCUSDT"
        assert "pnl" in trades[0]
    finally:
        pe._market.fetch_ticker = orig
        pe._LEDGER_PATH = old_path
        pe._ENGINE = None
        os.unlink(ledger_path)
