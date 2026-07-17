# Frontend Architecture — Day-Trader Platform

> Status: design draft (pre-build). Companion to `memory/2026-07-17.md` frontend audit.
> Scope: transform `dashboard/` (React "Signal Terminal") into a full day-trader desk where
> **agents analyze + execute (paper)** using metrics, indices, and news. Constraint: **paper-only**,
> Binance public data only, no real-money path.

## 1. Current state (audit summary)

| Surface | File(s) | Reality | Grade |
|---|---|---|---|
| Dashboard | `Dashboard.tsx` | 3 internal tabs (dashboard/browse/scoring); equity poll `/equity` 5s | B |
| Signal Terminal | `ScorePanel.tsx` | SVG arc gauge + segment bar; **synthetic** `genSeries`; `/api/score`, `/api/llm-signal` | A |
| Browse | `BrowseStrategies.tsx` + `browse/*` | lists **3 mock** strategies; `StrategyCard.forkUrl` external | C (mock) |
| Analyze | `AnalyzePage.tsx` | backtest form + reflection; real `/api/backtest` | B |
| Report | `BacktestReport.tsx` (ReportView) | full report: KPIs, equity, trades, reflection | A- |
| Agent analysis | `AgentAnalysisCard.tsx` + `agent_analyzer.py` | rule-based `ok/warn/alert`, not a committee | B |

Backend today (`core/strategy_api.py`): FastAPI serving SPA + REST.
`GET /api/strategies` returns **hardcoded `STRATEGIES_MOCK`**; `POST /api/score`,
`POST /api/llm-signal`, `POST /api/backtest` (strategy=llm, use_scoring),
`GET /api/backtest/{id}`, `POST /api/backtest/{id}/reflection`.
No `/metrics`, `/health`, live market, indices, or news endpoints.

### Critical gaps vs vision
1. **No live market data** in UI (indicators engine `core/indicators.py` unused by frontend).
2. **No indices** (dominance, Fear&Greed, live tickers).
3. **No news/sentiment** pillar at all.
4. **Agents = 2 loose functions**, no visible multi-agent committee / decision log.
5. **Scoring is manual + synthetic** (ScorePanel `genSeries`); not driven by real closes.
6. **No execution UI** (Trade Desk, orders, live PnL, risk panel) — paper only.
7. **Nav split**: in-app tabs + orphan router routes (`/analyze`, `/backtest/:id`) not in top-nav.

## 2. Target architecture

### 2.1 Persistent left sidebar (single source of nav)
```
Dashboard · Markets · Signals · Agents · News · Trade Desk · Backtests · Strategies
```
- Routes consolidated in `main.tsx` (keep `react-router-dom`); sidebar mirrors routes.
- Top bar: paper/live toggle (paper-locked), clock, connection status, account equity chip.

### 2.2 Tab responsibilities
- **Dashboard** — composite: equity curve, today's KPIs, active signals feed, agent-desk summary.
- **Markets** — watchlist (BTC/ETH/SOL…) live price + 24h change + sparkline; click → indicator drawer.
- **Signals** — live scoring feed: per symbol/timeframe, score gauge + verdict + trigger; auto-refresh from real closes.
- **Agents** — Agent Desk: per-cycle agent cards (Metrics / News / Risk / Strategy / Decision Core) with verdict + confidence + reasoning (transparent log / "chatroom").
- **News** — aggregated headlines + sentiment tags + impact flag per asset.
- **Trade Desk** — paper positions, open orders, PnL, risk panel (exposure, daily loss, cooldown), execute/close buttons (paper).
- **Backtests** — run + list + open report (existing Analyze + Report, promoted).
- **Strategies** — real strategy registry from backend (replaces `STRATEGIES_MOCK`).

## 3. Backend endpoints to add (paper-only)

| Method | Path | Purpose | Maps to |
|---|---|---|---|
| GET | `/api/market/overview` | watchlist tickers + 24h | Markets |
| GET | `/api/indicators` | `?symbol=&tf=` RSI/MACD/BB/ATR from `indicators.py` | Markets/Signals |
| GET | `/api/indices` | BTC dominance, Fear&Greed, altseason | Markets |
| GET | `/api/news` | headlines + sentiment + impact | News |
| WS  | `/ws/signals` | live scored signals stream | Signals |
| GET | `/api/agents/cycle` | last agent-desk cycle (all agents) | Agents |
| GET | `/api/positions` | paper positions + orders + PnL | Trade Desk |
| POST | `/api/orders` | paper market order (risk-gated) | Trade Desk |
| GET | `/api/risk/state` | exposure, daily loss, cooldown | Trade Desk |
| GET | `/api/metrics` | counters (signals, orders, rejections) | observability |
| GET | `/api/health` | liveness + exchange reachability | observability |

### Risk pipeline (refactor `core/risk.py` — from reference #3)
Ordered gate, first reject aborts, caps continue adjusted:
```
1 symbol allowlist (reject)
2 max position size (cap)
3 per-symbol exposure cap (reject)
4 total exposure cap (reject)
5 leverage cap (cap)
6 daily loss limit (reject)
7 cooldown after loss (reject)
8 max spread pct (reject)
```
Plus: **idempotency** (`request_id` + TTL), **trailing stop to break-even**, **A/B/C signal grading + no-trade zone** folded into `core/scoring.py`.

## 4. Reference mapping

| Source | Borrowed concept | Lands in |
|---|---|---|
| LLM-TradeBot (#1) | multi-agent pipeline + Agent Chatroom + DecisionCore fusion | Agents tab, `/api/agents/cycle` |
| ai-trader-for-mt4 (#2) | ReAct SOP loop, Trading Law (2%/9% rules), A/B/C grading, dynamic SL+ATR, news search | Scoring, Risk, News |
| ai-automated-trading-bot (#3) | ordered risk gate, idempotency, `/metrics`, `/health`, trailing stop, DRY_RUN | risk.py, strategy_api.py, Trade Desk |

## 5. Build phases

**Phase 0 — Unblock (do first)**
- Replace `STRATEGIES_MOCK` with real registry endpoint (`GET /api/strategies` from `registry.py`).
- Wire ScorePanel to real closes (drop `genSeries`); poll or WS.
- Add `/api/health`, `/api/metrics` to `strategy_api.py`.

**Phase 1 — Market + Signals**
- `/api/market/overview`, `/api/indicators`, `/api/indices`.
- Markets tab + Signals tab (live gauge feed).

**Phase 2 — Agent Desk + News** — **DONE (2026-07-17)** ver `frontend-phase2-plan.md`.
- Agent orchestration module (Metrics/News/Risk/Strategy/DecisionCore) reusing `agent_analyzer` + new news agent.
- `/api/agents/cycle`, `/api/news`. Agents + News tabs.

**Phase 3 — Trade Desk (paper)**
- `core/risk.py` ordered gate + idempotency + trailing stop.
- `/api/positions`, `/api/orders`, `/api/risk/state`. Trade Desk UI.

**Phase 4 — Polish**
- Unified sidebar nav; paper/live toggle (paper-locked); connection status; a11y pass.

## 6. Decisions / constraints
- Real-money OUT of scope (constraint + all references warn demo-only).
- Keep React + FastAPI; no new heavy deps.
- News source: free RSS / public crypto news API (no paid key required for MVP).
- LLM client stays stdlib `urllib`; generalize to multi-provider later.

## 7. Next actions
1. Commit uncommitted work (DP docs + market_ws fix + CB brief — see memory).
2. Start Phase 0: real strategies endpoint + ScorePanel live data + health/metrics.
3. Then Phase 1 endpoints + Markets/Signals tabs.
