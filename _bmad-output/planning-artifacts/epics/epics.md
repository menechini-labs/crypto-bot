---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - "conversation: day trader dashboard (2026-07-18)"
  - "codebase: core/, dashboard/src/"
  - "research: domain-crypto-day-trading-dashboard-research-2026-07-18"
workflowType: epics
lastStep: 3
project_name: crypto-bot
date: '2026-07-18'
user_name: Adilsonmenechini
---

# crypto-bot - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for crypto-bot, decomposing the requirements from user conversation, existing codebase analysis, and domain research into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Day trader dashboard must display real-time metrics (price, equity, P&L) updating live without page refresh
FR2: Trader must be able to select multiple coins (BTC, ETH, SOL, etc.) to monitor simultaneously
FR3: System must support running multiple trading agents concurrently, each assigned to a different coin
FR4: Dashboard must show agent verdicts (buy/sell/hold) per coin with confidence scores and reasoning
FR5: Trader must be able to start/stop individual agents per coin
FR6: System must aggregate and display portfolio-level P&L across all active coins
FR7: Dashboard must show per-coin positions (qty, avg price, unrealized P&L)
FR8: Trader must be able to switch between DEMO and REAL (paper) execution mode
FR9: System must persist agent decision history for review
FR10: Trader must be able to configure per-agent risk parameters (SL%, TP%, trailing)
FR11: System must gracefully handle exchange WebSocket disconnects and reconnect with state recovery
FR12: Dashboard must provide a historical equity chart for any date range

### NonFunctional Requirements

NFR1: Real-time metrics must update with latency under 1 second from market event to dashboard display
NFR2: Multi-agent execution must not block — one agent's operation must not delay another's
NFR3: Dashboard must maintain responsive UI (60fps) when streaming 5+ coins simultaneously
NFR4: WebSocket reconnection must complete within 5 seconds of disconnect detection
NFR5: Agent state must be recoverable after server restart (ephemeral but last-known-state logged)
NFR6: Browser must handle WebSocket message rate of at least 100 msg/s without jank
NFR7: Historical data queries must return within 2 seconds for up to 30 days of 1m candles

### Additional Requirements

- FastAPI backend already serves REST API — extend with WebSocket endpoints for real-time push
- React SPA already exists (Vite build) — add WebSocket client layer alongside existing polling
- Strategy registry plugin system exists — each coin gets its own strategy instance
- PaperEngine exists for single-position — extend to multi-coin, multi-position
- AgentDesk 5-agent cycle exists — extend to per-coin agent teams
- Existing polling pattern (5s equity, 30s agents, 10s loop) must coexist with WebSocket during migration
- No data persistence layer exists yet — equity/history served from in-memory array in paper_engine
- All config goes through config_loader.py (YAML-based)

### UX Design Requirements

(No UX design contract exists — will be derived from existing React component patterns)

### FR Coverage Map

| FR  | Epic | Description |
|-----|------|-------------|
| FR1 | Epic 1 | Real-time metrics push via WebSocket |
| FR2 | Epic 2 | Multi-coin selection UI |
| FR3 | Epic 3 | Concurrent agent execution per coin |
| FR4 | Epic 3 | Agent verdicts displayed per coin |
| FR5 | Epic 3 | Start/stop individual agents per coin |
| FR6 | Epic 4 | Portfolio-level P&L aggregation |
| FR7 | Epic 2 | Per-coin positions display |
| FR8 | Epic 3 | DEMO/REAL mode switching |
| FR9 | Epic 4 | Decision history persistence |
| FR10 | Epic 3 | Per-coin risk parameters (SL/TP/trailing) |
| FR11 | Epic 5 | Graceful WebSocket reconnect |
| FR12 | Epic 2 | Historical equity chart |

## Epic List

### Epic 1: Real-Time WebSocket Infrastructure

Stream live prices, equity snapshots, and agent verdicts to the dashboard via WebSocket, replacing polling. Traders see market moves and agent decisions instantly.
**FRs covered:** FR1, NFR1, NFR4, NFR6

### Epic 2: Multi-Coin Dashboard

Select multiple coins simultaneously via a searchable selector. Each coin gets its own panel with positions, equity history, and agent verdicts. Consolidated positions table across all coins.
**FRs covered:** FR2, FR7, FR12

### Epic 3: Concurrent Multi-Agent Execution

Run an independent agent cycle per coin with isolated strategy instances, per-coin PaperEngine state, per-coin risk config, and a shared portfolio-level risk guard. DEMO/REAL mode works per session.
**FRs covered:** FR3, FR4, FR5, FR8, FR10, NFR2

### Epic 4: Portfolio-Level Metrics and History

Aggregate portfolio equity across all coin positions, persist history to disk, expose per-coin Sharpe/win-rate/drawdown metrics via the Scoring tab.
**FRs covered:** FR6, FR9, NFR7

### Epic 5: Resilience and Observability

WebSocket reconnection with state recovery, agent crash isolation (one coin's exception doesn't kill others), per-coin health endpoint, structured JSON logging with coin/cycle context.
**FRs covered:** FR11, NFR3, NFR5

---

---

## Epic 1: Real-Time WebSocket Infrastructure

Replace polling with WebSocket push for market data, equity updates, and agent verdicts. This is the foundational layer every other epic depends on.

### Story 1.1: Backend WebSocket Endpoint

As a developer,
I want a FastAPI WebSocket endpoint (`/ws`) that streams market price, equity snapshot, and agent verdicts,
So that frontend receives real-time data without polling.

**Acceptance Criteria:**

**Given** the server is running and a client connects to `/ws`
**When** the client sends a `{"subscribe": {"coins": ["BTCUSDT", "ETHUSDT"]}}` message
**Then** the server starts streaming per-coin price updates at 1s intervals
**And** the server streams equity snapshots whenever paper_engine processes a new cycle
**And** the server streams agent verdicts when any per-coin agent cycle completes
**And** disconnecting does not crash the server; reconnecting resumes streams

### Story 1.2: Frontend WebSocket Client Hook

As a trader,
I want the dashboard to connect to the WebSocket endpoint and display live-updating values,
So that I see price, equity, and agent changes without waiting for polling intervals.

**Acceptance Criteria:**

**Given** the dashboard is loaded
**When** the WebSocket connection establishes
**Then** the existing polling fallback (5s/30s/10s) remains active but does not override WebSocket values
**And** if WebSocket disconnects, polling takes over seamlessly within 1 missed heartbeat
**And** on reconnect, WebSocket resumes as primary data source
**And** the connection status indicator shows "Live" / "Polling fallback" accurately

### Story 1.3: WebSocket Auth and Session Identity

As a trader,
I want the WebSocket connection to be tied to my DEMO/REAL mode session,
So that I receive the correct portfolio state.

**Acceptance Criteria:**

**Given** the trader is in DEMO mode
**When** the WebSocket connects
**Then** the server associates the connection with the current paper_engine mode
**And** toggling DEMO ↔ REAL via the sidebar button resubscribes the WebSocket with the new mode

---

## Epic 2: Multi-Coin Dashboard

Transform the single-coin dashboard into a multi-coin trading desk with per-coin panels and unified portfolio overview.

### Story 2.1: Multi-Coin Selection UI

As a trader,
I want a coin selector (searchable dropdown or grid of toggleable coins),
So that I can choose which assets to monitor and trade.

**Acceptance Criteria:**

**Given** the dashboard is loaded
**When** I open the coin selector
**Then** I see a searchable list of supported coins (BTCUSDT, ETHUSDT, SOLUSDT, etc.)
**And** I can select/deselect coins; selected coins appear as pinned tabs or panels
**And** my selection persists across page reloads (localStorage)

### Story 2.2: Per-Coin Agent Desk Panel

As a trader,
I want each selected coin to have its own Agent Desk panel showing per-coin agents and verdicts,
So that I can assess the situation for each asset independently.

**Acceptance Criteria:**

**Given** I have 3 coins selected
**When** the agent cycle completes for each coin
**Then** each coin's panel shows its own agent verdicts (MetricsAgent, NewsAgent, RiskAgent, StrategyAgent, DecisionCore)
**And** each panel shows its own confidence score and reasoning
**And** the panels update independently (one coin's slow cycle does not stall others)

### Story 2.3: Per-Coin Trade Controls

As a trader,
I want per-coin execution controls (SL%, TP%, trailing, auto-trade toggle),
So that I can configure risk differently for each asset.

**Acceptance Criteria:**

**Given** I have BTCUSDT and ETHUSDT active
**When** I set SL 2% for BTC and SL 3% for ETH
**Then** BTC agents use 2% SL, ETH agents use 3% SL
**And** configuration is persisted in server-side agent config per coin

### Story 2.4: Multi-Coin Positions Table

As a trader,
I want a consolidated positions view showing all open positions across coins,
So that I see my full exposure at a glance.

**Acceptance Criteria:**

**Given** agents have opened positions in BTC, ETH, and SOL
**When** I view the Positions tab
**Then** I see a table with columns: Coin, Qty, Avg Price, Current Price, Unrealized P&L, P&L%
**And** rows are sorted by unrealized P&L (most negative first)
**And** total portfolio exposure (sum of position values) is shown at bottom

---

## Epic 3: Concurrent Multi-Agent Execution

Extend the single-loop agent system to run independent agent cycles per coin concurrently, with proper isolation and shared risk controls.

### Story 3.1: Per-Coin Agent Loop Manager

As a developer,
I want a manager that runs an independent agent cycle for each active coin,
So that agents for BTC and ETH execute concurrently without blocking each other.

**Acceptance Criteria:**

**Given** BTCUSDT and ETHUSDT are both active
**When** the agent loop fires for both
**Then** both cycles start concurrently (asyncio.gather or TaskGroup)
**And** if ETH's news_agent hangs, BTC's cycle completes and executes independently
**And** a per-coin cycle timeout (default 30s) prevents any single coin from blocking the world

### Story 3.2: Per-Coin Strategy Instance Registry

As a developer,
I want each coin to have its own strategy instance from the plugin registry,
So that different coins can use different strategies with independent state.

**Acceptance Criteria:**

**Given** BTCUSDT uses "scalping" strategy and ETHUSDT uses "mean_reversion"
**When** a cycle runs for each
**Then** BTC's strategy instance maintains its own indicators state (no cross-contamination)
**And** each instance is isolated in memory, garbage-collected when coin is deselected

### Story 3.3: Multi-Coin PaperEngine

As a developer,
I want PaperEngine to manage multiple concurrent positions across coins,
So that orders for different coins do not interfere.

**Acceptance Criteria:**

**Given** PaperEngine holds a BTC long and an ETH short
**When** BTC hits SL and closes
**Then** ETH position remains open and continues tracking
**And** portfolio equity calculation sums positions across all coins
**And** fill/slip simulation is per-coin based on that coin's market data

### Story 3.4: Shared Risk Guard (Portfolio-Level)

As a trader,
I want a portfolio-level risk guard that can prevent new positions when total exposure exceeds a limit,
So that concurrent agents don't collectively over-leverage.

**Acceptance Criteria:**

**Given** portfolio max exposure is set to $10,000
**When** BTC position uses $8,000 and ETH agent tries to open a $5,000 position
**Then** ETH agent receives a "risk guard rejected: exposure limit" verdict
**And** the decision is logged with the rejecting guard reason

---

## Epic 4: Portfolio-Level Metrics and History

Add portfolio aggregation, historical equity tracking, and performance analytics.

### Story 4.1: Portfolio Equity Aggregator

As a trader,
I want a single portfolio equity value that reflects all coin positions,
So that I see my total P&L at a glance.

**Acceptance Criteria:**

**Given** I have positions in 3 coins
**When** equity is calculated
**Then** it equals sum of (coin_balance * current_price) across all coins, plus free cash
**And** P&L = current equity - (deposits) is displayed in the sidebar
**And** the value updates in real-time via WebSocket

### Story 4.2: Historical Equity Database

As a trader,
I want equity history persisted to disk (SQLite or JSONL),
So that I can review past performance after server restart.

**Acceptance Criteria:**

**Given** the server has been running for 7 days
**When** I reload the dashboard
**Then** the equity chart shows all 7 days of history (not just current session)
**And** I can zoom to any date range
**And** the data file does not grow unbounded (rotation or pruning older than N days)

### Story 4.3: Per-Coin Performance Metrics

As a trader,
I want per-coin performance stats (Sharpe, win rate, max drawdown, total P&L),
So that I can evaluate which strategies are working.

**Acceptance Criteria:**

**Given** BTC has been traded for 100 cycles
**When** I view the Scoring tab for BTC
**Then** I see Sharpe ratio, win rate, max drawdown, total P&L, and trade count for BTC only
**And** the same metrics are available for ETH separately, and for the whole portfolio

---

## Epic 5: Resilience and Observability

Robust reconnection, error recovery, logging, and health monitoring.

### Story 5.1: WebSocket Reconnection with State Recovery

As a trader,
I want the dashboard to survive network blips without losing state,
So that I don't miss price updates during a brief disconnect.

**Acceptance Criteria:**

**Given** the WebSocket disconnects
**When** the network recovers within 30 seconds
**Then** the client reconnects automatically
**And** the server resumes streaming the same subscriptions
**And** any missed equity snapshots are not replayed (idempotent — next snapshot is current)
**And** the "connection status" indicator transitions through states: connected → reconnecting → connected

### Story 5.2: Agent Crash Isolation

As a developer,
I want a single coin's agent crash to not affect other coins,
So that multi-agent execution is resilient.

**Acceptance Criteria:**

**Given** BTC agent raises an unhandled exception during its cycle
**When** the exception propagates
**Then** only BTC's cycle is marked as failed; ETH and SOL cycles continue
**And** the error is logged with traceback
**And** BTC is retried on the next cycle tick; repeated failures (3 consecutive) disable that coin's agent
**And** a warning badge appears on the disabled coin's panel

### Story 5.3: Health Endpoint with Per-Coin Status

As a developer,
I want the `/api/health` endpoint to report per-coin agent status,
So that I can monitor which coins are active, stalled, or errored.

**Acceptance Criteria:**

**Given** BTC is running, ETH is errored, SOL is disabled
**When** I GET /api/health
**Then** the response includes:
```json
{
  "mode": "demo",
  "coins": {
    "BTCUSDT": { "status": "running", "last_cycle_ok": true },
    "ETHUSDT": { "status": "errored", "last_error": "news_agent timeout", "fail_count": 2 },
    "SOLUSDT": { "status": "disabled", "reason": "3 consecutive failures" }
  }
}
```
**And** the HealthPanel frontend tab renders this data with color-coded status badges

### Story 5.4: Structured Logging and Audit Trail

As a developer,
I want all agent decisions, orders, and errors logged with structured context (coin, cycle_id, agent_name),
So that I can debug issues across multiple concurrent agents.

**Acceptance Criteria:**

**Given** agents are running for multiple coins
**When** an order is placed, agent verdict reached, or error occurs
**Then** the log line includes: timestamp, coin, cycle_id, agent_name, verdict/action, duration_ms
**And** logs are written in JSON format for log aggregation tools
**And** log level is configurable via config.yaml per-module (core.*)
