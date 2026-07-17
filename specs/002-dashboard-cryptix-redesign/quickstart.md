# Quickstart: Dashboard Cryptix Redesign

**Feature**: 002-dashboard-cryptix-redesign
**Branch**: feature/dashboard-cryptix-redesign

End-to-end verification that the restyle works without breaking data or tests.
No backend changes — the API must be running on `:8000` (or use Vite proxy dev
mode which forwards `/api` and `/equity`).

## Prerequisites

- Node + npm (project uses Vite/Biome/Vitest as configured in `dashboard/package.json`).
- The crypto-bot API service reachable (default `:8000`) so the dashboard has data.
  Alternatively start the API in paper mode per project docs.

## Setup & Run

```bash
cd dashboard
npm install        # only if node_modules absent
npm run dev        # Vite on :5173, proxies /api and /equity to :8000
```

Open http://localhost:5173/

## Validation Scenarios (proves feature works)

### S1 — Dashboard (US1)
1. Load `/`. Expect: portfolio equity, P&L, drawdown, win-rate stat cards render
   in the new Cryptix theme (rounded cards, soft shadow, blue accent, Inter font).
2. Expect: equity curve (`EquityChart`) renders with positive/negative coloring.
3. Expect: reflections list renders.
4. Expect: tab switch Overview/Positions works.

### S2 — Browse & Analysis (US2)
1. Go to Browse. Expect: strategy grid uses the new card style; filters bar usable.
2. Apply a filter (e.g., symbol). Expect: grid updates.
3. Open a strategy card → run a backtest (`BacktestRunner`). Expect: results + agent
   analysis (`AgentAnalysisCard`) render in new theme.
4. Open `/backtest/:id` and `/analyze` routes. Expect: themed, no layout breakage.

### S3 — States (FR)
1. Empty equity → `.empty` message styled, not broken.
2. Loading / error states styled consistently.

### S4 — Lint & Tests (FR-007)
```bash
npm run lint        # Biome must pass (no new errors)
npm run test        # Vitest suites green
```
Optional e2e: `npm run test:e2e` (Playwright) if configured.

## Expected Outcome
New coherent theme across both surfaces, **all previously displayed data still
present**, no console errors, Biome clean, Vitest green. Exact palette adjustable
via the token block in `dashboard/src/index.css` (FR-008).
