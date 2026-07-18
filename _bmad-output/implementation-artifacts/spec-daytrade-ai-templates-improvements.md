---
title: 'Day-Trade Platform Improvements: AI-Driven Minute Indicators + Ready-Made Strategy Templates'
type: 'feature'
created: '2026-07-18'
status: 'in-progress'
baseline_revision: '4ca3d85ca0eb02a1860b07f01c0eaf54b51b6f29'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** The crypto-bot has rule-based indicators, an LLM decision core, and 7 strategies, but lacks intraday-specific indicators (VWAP/ATR/stochastic), a dedicated 1-minute analysis loop, and a curated set of named, copy-paste day-trade strategy templates users can launch in one click.

**Approach:** Add intraday indicators + a stateful 1m signal engine, wire AI (LLM + optional ML slot) for per-minute decisions, and ship ≥5 ready-made day-trade templates (scalping, breakout, mean-reversion, grid, trend-following, range-bound, contrarian) selectable from the Agent Desk / swarm presets.

## Boundaries & Constraints

**Always:** Keep stdlib-only where possible; reuse `core/market_ws.py` 1m kline feed (no new polling loop); LLM stays env-gated (`ENABLE_LLM`); real-trading guard (`MODE=real` + `ALLOW_LIVE_TRADING=1`) untouched; rule-based fallback preserved on LLM failure.

**Block If:** Any change that relaxes the live-trading guard, or requires paid external ML services without user approval.

**Never:** Replace the existing 7 registered strategies; introduce train/live divergence (backtest and live must reuse same strategy code); depend on external paid data feeds.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | 1m kline closed + indicators computed | Signal fired once per bar (stateful) | No error expected |
| ERROR_CASE | LLM API down / disabled | Fall back to rule-based decision | Log + continue |
| ERROR_CASE | `grid_dynamic` invoked | Must not reference undefined `ccloses`/`closes` | Fix bug before template ships |

</intent-contract>

## Code Map

- `core/indicators.py` -- add VWAP, ATR, stochastic (stdlib) for intraday
- `core/market_ws.py` -- already streams 1m klines (`WebSocketMarket`); reuse for signal engine
- `core/strategy_api.py` -- `_agent_loop_worker` polls `fetch_ohlcv`; add optional 1m stateful signal path
- `core/agent_desk.py` -- `_llm_decision_core`; keep hybrid (ML score + rule risk layer)
- `core/strategy_registry/` -- 7 strategies exist; add template wrappers (scalping/breakout/mean-reversion/grid/trend/range/contrarian)
- `core/swarm_presets.py` -- 6 presets; add day-trade template presets
- `core/backtest.py` -- reuse for 1m backtest preset
- `dashboard/src/AgentDesk.tsx` -- add template selector UI

## Tasks & Acceptance

**Execution:**
- [ ] `core/indicators.py` -- add `vwap`, `atr`, `stochastic` functions (stdlib) -- intraday signal quality
- [ ] `core/strategy_registry/` -- add `scalping`, `breakout`, `mean_reversion`, `range_bound`, `contrarian` template strategies; fix `grid_dynamic` undefined vars -- ≥5 ready templates
- [ ] `core/swarm_presets.py` -- add day-trade template presets referencing new strategies -- one-click launch
- [ ] `core/strategy_api.py` -- add stateful 1m signal engine (fires once per closed bar) reusing `market_ws` -- per-minute analysis
- [ ] `core/agent_desk.py` -- ensure LLM decision core consumes 1m indicators + keeps rule fallback -- AI per minute
- [ ] `dashboard/src/AgentDesk.tsx` -- add template dropdown bound to presets -- UX
- [ ] `tests/unit/test_daytrade_templates.py` -- unit test each template + indicator math -- verify

**Acceptance Criteria:**
- Given 1m kline stream, when a bar closes, then a signal fires at most once per bar (stateful, no duplicate).
- Given `ENABLE_LLM=0`, when decision runs, then rule-based fallback returns a valid signal.
- Given template selected, when loop starts, then the matching strategy drives decisions.
- Given `grid_dynamic` invoked, then no `NameError` on `ccloses`/`closes`.

## Design Notes

Templates are thin wrappers over existing indicator primitives (VWAP/ATR/Stochastic + RSI/MACD/BB) with preset params, mirroring Freqtrade's `IStrategy` populate_entry/exit pattern. The 1m engine reuses `WebSocketMarket.on_new_candle` rather than a new poller, preventing train/live drift. AI layer stays hybrid: LLM scores candidates, rule layer enforces sizing/kill-switch (per web research: hybrid decision core is industry standard).

## Verification

**Commands:**
- `.venv/bin/python -m pytest tests/unit/test_daytrade_templates.py -q` -- expected: all pass
- `.venv/bin/python -c "import core.indicators as i; print(i.vwap([]))"` -- expected: no error
- `cd dashboard && npx tsc --noEmit && npx vitest run` -- expected: clean

**Manual checks:**
- `/api/agents/cycle?team=<daytrade_template>` returns a decision using 1m indicators
