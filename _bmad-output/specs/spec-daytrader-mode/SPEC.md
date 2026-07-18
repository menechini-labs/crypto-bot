---
id: SPEC-daytrader-mode
companions:
  - path-audit.md     # All project paths — what each does, how mode affects it
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Day-Trader Platform — Demo vs Real Mode

## Why

A day-trader platform must separate **data observation** from **capital execution**. A user exploring strategies, testing new indicators, or learning the market should see the same real-time data without risking capital. Only when they explicitly opt in does execution activate. This is the foundational safety and interaction model of the platform.

The current codebase has a `paper` mode but no exposed toggle — it's hardcoded in `Dashboard.tsx`, gated by env var at the executor level. The user wants a first-class, visible, user-controlled mode switch that transforms the UI and API behavior accordingly.

## Capabilities

- **CAP-1 — Mode toggle (sidepanel)**
  - **intent:** User switches between DEMO and REAL mode from the sidebar at any time. A confirmation dialog prevents accidental activation of REAL mode.
  - **success:** Clicking the toggle in sidebar shows a dialog. Confirming switches mode. Visual indicators (badge, color, text) update immediately. /api/health reflects the new mode.
- **CAP-2 — DEMO mode (observation only)**
  - **intent:** In DEMO mode, all market data, strategies, backtests, scoring, news, agents, and signals display live real-time data but no order submission is accepted.
  - **success:** Trade Desk shows "disabled in DEMO mode" with buy/sell buttons disabled. API returns error on /api/orders. All other endpoints work identically.
- **CAP-3 — REAL mode (paper execution)**
  - **intent:** In REAL mode, the full system operates including paper execution against live Binance ticker. RiskManager gates are active.
  - **success:** /api/orders executes paper fills. Trade Desk shows active buy/sell buttons. Positions appear and PnL updates. Equity chart grows.
- **CAP-4 — Mode persistence**
  - **intent:** Selected mode survives server restarts. Stored in `.env` or `config.yaml` so the system boots in the last-used mode.
  - **success:** Restart server, switch to REAL, restart again — mode reads back as REAL without user interaction.

## Constraints

- REAL mode MUST require `ALLOW_LIVE_TRADING=1` env var at process level before the in-app toggle has any effect. Without it, the toggle stays locked to DEMO.
- All Binance data uses public no-auth endpoints. No API key stored or transmitted.
- UI must visually distinguish DEMO vs REAL at all times — sidebar badge + backdrop/header color. User must never guess which mode is active.
- Single frontend codebase. Same pages, same endpoints. Mode only changes execution gates and visual presentation.
- DEMO is the default on first boot. REAL must be explicitly chosen.

## Non-goals

- Real-money exchange adapter. REAL mode = paper execution against live market data.
- Multi-user, auth, permissions, or workspaces.
- Separate DEMO-only vs REAL-only builds or branches.

## Success signal

A user opens the app, sees live data, switches to REAL with confirmation, submits a paper order, sees it fill, sees the equity chart update, and can switch back to DEMO to stop execution — all from the sidebar, all in one browser session, without restarting the server.

## Assumptions

- User wants a single toggle in the sidebar, not separate installs for demo vs real.
- DEMO mode is the default. REAL mode requires explicit toggle + confirmation.

## Open Questions

- Should REAL mode auto-disconnect after X minutes of inactivity as a safety measure?
- Should a scheduled mode timer exist (e.g., "auto-revert to DEMO at market close")?
- Should the confirmation dialog include a configurable timeout before the switch takes effect?
