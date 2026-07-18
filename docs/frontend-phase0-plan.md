# Phase 0 Plan — Unblock the Day-Trader Frontend

**STATUS: DONE (2026-07-17)** — commit `69849db` + `966e235` + `64a5162`.

Companion to `frontend-daytrader-architecture.md`. Concrete, file-level steps.
Goal: remove fake data + synthetic scoring, add observability, expose real strategies.
Constraint: paper-only, Binance public data, no new heavy deps.

---

## 0.1 Replace `STRATEGIES_MOCK` with real registry

**Backend** `core/strategy_api.py`:
- Today: `GET /api/strategies` returns hardcoded `STRATEGIES_MOCK`.
- Change: import `from core.strategy_registry.registry import get_all` and build response from `get_all()` keys.
- Response shape must satisfy frontend `Strategy` type (`dashboard/src/browse/types.ts`):
  `id, name, symbol, timeframe, author, netProfitPct, profitFactor, maxDrawdownPct, winRatePct, sharpeRatio, sortinoRatio, totalTrades, equityCurve, forkUrl`.
- For MVP: static metadata per strategy (no fake PnL). Emit `netProfitPct: null`, `equityCurve: []`, `forkUrl: ""`, `author: "core"`, `timeframe: "1h"`, `symbol: "BTCUSDT"`. Mark `hasBacktest: false`.
- Add optional query `?symbol=&tf=` to scope defaults.

**Frontend** `dashboard/src/browse/StrategyCard.tsx`:
- Guard `forkUrl`: if empty, render disabled/"—" instead of external link.
- If `netProfitPct == null`, show "Run backtest" CTA (already has Analyze link) instead of a PnL number.
- `BrowseStrategies.tsx`: already polls `/api/strategies` every 30s — keep; remove reliance on mock shape.

**Frontend** `dashboard/src/browse/types.ts`:
- Add `hasBacktest?: boolean` to `Strategy`.

---

## 0.2 Make Signal Terminal use REAL data (kill `genSeries`)

**Frontend** `dashboard/src/ScorePanel.tsx`:
- Remove `genSeries()` synthetic series.
- Add `useEffect` that fetches real closes: new backend `GET /api/market/closes?symbol=BTCUSDT&tf=1h&limit=60` (see 0.4) OR reuse Binance directly. Prefer backend to stay single-source.
- Feed real `closes` into `POST /api/score` and `POST /api/llm-signal`.
- Show loading state while fetching; auto-refresh every 30–60s.
- Keep gauge/segment visuals; bind them to real `score_signal` response.

**Backend** `core/strategy_api.py`:
- `POST /api/score` already expects `{closes, signal, has_position, ctx?}`. Good.
- Ensure response includes `score`, `confidence`, `risk`, `verdict`, `reasons` (already in `core/scoring.score_signal`).

---

## 0.3 Add observability: `/api/health` + `/api/metrics`

**Backend** `core/strategy_api.py`:
- `GET /api/health` → `{"status":"ok","exchange":"binance","mode":"paper","time":<iso>}`.
  - Optionally ping Binance `/api/v3/ping` (public, no auth) to set `exchange:"reachable"|"down"`.
- `GET /api/metrics` → JSON counters dict, module-level:
  ```python
  _METRICS = {"signals_scored":0,"llm_calls":0,"llm_errors":0,
              "backtests_run":0,"orders_paper":0,"risk_rejections":0}
  ```
  - Increment in `/api/score` (`signals_scored`), `/api/llm-signal` (`llm_calls`/`llm_errors`), `/api/backtest` (`backtests_run`).
- Add `GET /api/risk/state` stub returning paper defaults (exposure=0, daily_loss=0, cooldown=false) — filled in Phase 3.

**Frontend**: no UI yet in P0; endpoints exist for later Trade Desk + status chip.

---

## 0.4 Add market data endpoint (feeds Signals + Phase 1 Markets)

**Backend** `core/strategy_api.py`:
- `GET /api/market/closes?symbol=BTCUSDT&tf=1h&limit=60` → fetch from Binance `GET /api/v3/klines` (public), return `{symbol, tf, closes:[...]}`.
- `GET /api/market/overview?symbols=BTCUSDT,ETHUSDT,SOLUSDT` → for each, last price + 24h change from `/api/v3/ticker/24hr`. (Used by Markets tab in P1; safe to add now.)
- Cache klines 5s to avoid rate limits.

**Reuse**: `core/market.py` likely has fetch helpers — check before writing new client. Prefer `core/market.py.get_klines(...)`.

---

## 0.5 Unify nav (prep for sidebar)

**Frontend** `dashboard/src/main.tsx`:
- Routes today: `/` (Dashboard), `/backtest/:id` (BacktestReport), `/analyze` (AnalyzePage).
- P0: keep routes; add a shared `<Layout>` with placeholder left rail listing future tabs (Dashboard active; others "soon"). Real sidebar in Phase 1/4.
- Ensure `AnalyzePage` and `BacktestReport` reachable from Dashboard/Browse (they already link). Add top-nav consistency: Dashboard header shows links to Browse/Analyze.

**Frontend** `dashboard/src/Dashboard.tsx`:
- Add nav chips: `Browse` (`/browse` via internal tab) and `Analyze` (`/analyze`).
- Keep internal tabs (dashboard/browse/scoring) for now; sidebar comes later.

---

## 0.6 Consistency fixes found during audit

- `BacktestReport.tsx` reads `report.profit_factor`, `report.sortino`, `report.calmar` — ensure `core/backtest.py` returns these (or frontend guards with `?.`). Verify against `BacktestReport` type.
- `AnalyzePage.tsx` / `BacktestRunner.tsx` / `BacktestReport.tsx` each re-declare `STRATEGIES = [...,"default"]` (no `"llm"`). Add `"llm"` option so LLM strategy is selectable in UI (currently only via `/api/llm-signal`). Validate backend `_VALID_STRATEGIES` includes `"llm"` (it does).
- `StrategyCard.forkUrl` external-only — disabled when empty (0.1).

---

## 0.7 Tests

- `tests/unit/test_strategy_api.py` (new or extend): assert `/api/strategies` returns registry keys (not mock), `/api/health` 200, `/api/metrics` 200, `/api/market/closes` returns list.
- Run via `.venv` + `uv pip install --python .venv/bin/python pytest` (no pip in venv).

## 0.8 Commit
Branch `feature/bmad-document-project` (or new `feature/daytrader-phase0`).
Include: DP docs, market_ws fix, CB brief, architecture docs, this plan, P0 code.
Message (EN): `feat: phase0 unblock — real strategies, live scoring, health/metrics`.
