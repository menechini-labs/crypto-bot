# Epic 1 Context: Real-Time WebSocket Infrastructure
<!-- Generated from planning artifacts. Regenerate via compile-epic-context if planning docs change. -->

## Goal

Replace 5s/30s/10s polling with WebSocket push for market price data, equity snapshots, and agent verdicts. Traders see market moves and agent decisions instantly with sub-second latency. This foundational layer enables all downstream epics (multi-coin layout, concurrent agents, portfolio metrics, resilience).

## Stories

- Story 1.1: Backend WebSocket Endpoint
- Story 1.2: Frontend WebSocket Client Hook

## Requirements & Constraints

- WebSocket stream must deliver market price, equity snapshot, and agent verdict updates in real time (<1s from event to dashboard display)
- Client subscribes/unsubscribes per-coin feeds via message protocol; server pushes only subscribed data
- Existing polling fallback (5s equity, 30s agents, 10s loop) must remain active alongside WebSocket during migration; polled values must never override fresher WebSocket data — WebSocket source takes precedence when connected
- Dashboard must maintain 60fps responsiveness when streaming 5+ coins simultaneously — frontend hook must batch or throttle updates to avoid render flooding
- Server handles disconnect gracefully without crash; reconnecting client resumes streams from current state, no message replay needed (latest snapshot only)
- DEMO/REAL mode switch triggers WebSocket resubscription with updated mode context; server tailors equity data to active mode
- Connection parameters (URL, heartbeat interval, reconnect backoff) must be config-driven via config.yaml
- WebSocket message format must support typed payload dispatch: price, equity_snapshot, agent_verdict — each with coin identifier for frontend routing
- Heartbeat/ping-pong required to detect stale connections; missing heartbeats trigger client-side reconnect

## Technical Decisions

- Server endpoint: FastAPI native WebSocket at `/ws` with JSON message protocol — `{"type": "subscribe", "coins": ["BTCUSDT"]}` / `{"type": "unsubscribe", "coins": [...]}`
- Push message types: `price_update`, `equity_snapshot`, `agent_verdict` — each scoped to coin identifier for frontend dispatch
- Frontend: React hook (`useWebSocket`) manages connect/disconnect/reconnect lifecycle, message dispatch to store slices, polling fallback state
- WebSocket server hooks into existing agent cycle completion events via event bus or callback; no polling needed for verdict detection
- Server maintains per-connection subscription map; disconnect triggers cleanup — no persistent session state
- No message replay or backfill on reconnect; client receives next snapshot when it occurs (idempotent by design)
- Heartbeat interval configurable via config.yaml; n+1 missed pings trigger reconnect
- Polling fallback activates only when WebSocket state is not "connected"; hook tracks both sources and uses WebSocket timestamp to resolve conflicts — polled values never overwrite fresher WS values
- Connection to paper engine is read-only — WebSocket server reads latest equity/market/verdict state, does not execute trades
- Existing in-memory equity history (paper_engine) serves as initial data source; future persistence adds historical replay later
- Subscription message must include mode (DEMO/REAL) so server returns correct equity context
- All per-coin streams are independent — slow market data for one coin does not block verdict delivery for another
- Backend uses asyncio tasks per WebSocket connection; configurable max concurrent connections to prevent resource exhaustion

## Cross-Story Dependencies

- Story 1.2 depends on Story 1.1 being operational
- Epic 1 is consumed by Epics 2–5 (multi-coin dashboard, concurrent execution, portfolio metrics, resilience observability)
