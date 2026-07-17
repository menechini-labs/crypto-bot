# core/strategy_registry/llm_strategy.py
"""LLM strategy module (stdlib-only HTTP client).

Activate via .env:
  ENABLE_LLM=1
  LLM_API_KEY=***
  LLM_BASE_URL=https://api.openai.com/v1
  LLM_MODEL=gpt-3.5-turbo
"""
import json
import logging
import os
import random
import urllib.error
import urllib.request
from typing import Any

from .base import BaseStrategy
from .registry import register
from .prompts import get_prompt

log = logging.getLogger(__name__)

ENABLE_LLM = os.getenv("ENABLE_LLM", "0") == "1"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")


def _llm_request(prompt: str, max_tokens: int = 256) -> str:
    """POST prompt to LLM chat endpoint. No external SDK."""
    if not ENABLE_LLM:
        raise RuntimeError("LLM desativado (ENABLE_LLM=0)")
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY nao configurado")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        LLM_BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"].strip().lower()
    except urllib.error.HTTPError as e:
        log.error("LLM HTTP error %s: %s", e.code, e.read().decode())
        raise
    except Exception:  # noqa: BLE001 - fallback to hold upstream
        log.exception("LLM request failed")
        raise


def _validate_signal(raw: str, has_position: bool) -> str:
    """Clean LLM output into a single discrete signal."""
    raw = raw.strip().lower()
    # Avoid doubling exposure: never 'buy' when already in position.
    if has_position and "buy" in raw:
        return "hold"
    if "buy" in raw:
        return "buy"
    if "sell" in raw:
        return "sell"
    return "hold"


@register("llm")
class LLMStrategy(BaseStrategy):
    """LLM-driven strategy. Market analysis + risk guard prompt."""

    name = "llm"

    def decide(self, closes: list[float], has_position: bool, ctx: dict[str, Any] | None = None) -> str:
        ctx = ctx or {}
        if not ENABLE_LLM:
            log.warning("LLM desativado -> fallback hold")
            return "hold"
        if len(closes) < 10:
            log.warning("Dados insuficientes (<10 candles)")
            return "hold"

        base_prompt = get_prompt("default_llm").format(
            symbol=ctx.get("symbol", "BTCUSDT"),
            latest_price=f"{closes[-1]:.2f}",
            price_change_pct=f"{((closes[-1] - closes[-10]) / closes[-10]) * 100:.2f}",
            volume=f"{random.uniform(1000, 5000):.0f}",
            candles="\n".join(f"  - {c:.2f}" for c in closes[-10:]),
            position_status="open" if has_position else "flat",
            risk_tolerance=ctx.get("risk_tolerance", "moderate"),
            market_regime=ctx.get("regime", "lateral"),
        )

        if has_position:
            base_prompt += "\n" + get_prompt("risk_guard").format(
                symbol=ctx.get("symbol", "BTCUSDT"),
                entry_price=f"{closes[-1]:.2f}",
                sl_pct=ctx.get("sl_pct", 5),
                tp_pct=ctx.get("tp_pct", 10),
                risk_capital=f"{ctx.get('current_cash', 10000):.2f}",
                available_cash=f"{ctx.get('available_cash', 10000):.2f}",
                max_position_pct=ctx.get("max_position_pct", 0.5),
                volatility=ctx.get("volatility", 2.5),
                max_open_positions=ctx.get("max_open_positions", 5),
            )

        log.info("Enviando prompt ao LLM")
        try:
            raw = _llm_request(base_prompt)
            return _validate_signal(raw, has_position)
        except Exception:  # noqa: BLE001
            return "hold"
