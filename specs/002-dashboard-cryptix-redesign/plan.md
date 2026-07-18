# Implementation Plan: Dashboard Cryptix Redesign

**Branch**: `[feature/dashboard-cryptix-redesign]` | **Date**: 2026-07-17 | **Spec**: [spec.md](../specs/002-dashboard-cryptix-redesign/spec.md)

**Input**: Feature specification from `/specs/002-dashboard-cryptix-redesign/spec.md`

## Summary

Reskin the crypto-bot React frontend toward the modern "Cryptix" (Framer SaaS)
design language while preserving every currently displayed data surface and all
existing behavior. This is a **presentation-layer-only** change: the same React +
TypeScript (Vite) SPA, consuming the same FastAPI endpoints. Work centers on
centralizing design tokens (CSS variables) and restyling the two main surfaces —
the Dashboard (portfolio + equity curve) and Browse (strategy grid, filters,
cards, backtest runner, agent analysis) — plus loading/empty/error states, into
one coherent theme.

Technical approach: introduce a single token source in `dashboard/src/index.css`
(`:root` custom properties) and refactor component class names/CSS to consume
those tokens. No new dependencies, no routing changes (keep `main.tsx` routes), no
backend changes.

## Technical Context

**Language/Version**: TypeScript 5.x + React 18 (per `dashboard/package.json`)

**Primary Dependencies**: react, react-dom, react-router-dom (existing); Vite build;
Biome (lint/format); Vitest + Testing Library + Playwright (tests). No new deps.

**Storage**: N/A (no new persistence; runtime data via existing `/equity` etc.)

**Testing**: Vitest (`dashboard` unit/component tests) + Playwright (e2e). Existing
suites must stay green (FR-007).

**Target Platform**: Desktop/laptop web browser (primary); responsive graceful
degradation on narrow widths (FR-006).

**Project Type**: Frontend SPA (presentation layer of a Python/FastAPI service).

**Performance Goals**: No regression to current load/interaction feel; theme is
CSS-only (no heavy runtime cost).

**Constraints**: Must not alter API contracts or backend. Must preserve 100% of
displayed data (SC-001). Centralized tokens required (FR-008).

**Scale/Scope**: 2 surfaces (Dashboard, Browse) + shared shell/theme; ~10-12
component files restyled. No new features.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

> Note: `.specify/memory/constitution.md` was wiped earlier in this session; the
> v1.0.0 constitution's relevant principles are applied from memory and re-asserted
> below. (Constitution file should be restored — see tasks/Polish.)

| Principle | Status | Note |
|-----------|--------|------|
| I. Research-First | ✅ Pass | Current dashboard read (Dashboard.tsx, index.css, StatCard, EquityChart, BrowseStrategies, main.tsx, types) before planning |
| II. Specify & Plan | ✅ Pass | spec.md + this plan exist |
| III. Task Decomposition | ✅ Pass | `/speckit.tasks` to follow |
| IV. TDD | ✅ Pass (target) | Existing Vitest/Playwright suites must stay green after restyle |
| V. SDD | ✅ Pass | Design follows spec user stories / FRs / SCs |
| VI. Coding discipline | ✅ Pass | Smallest correct change; centralized tokens; no new deps; no backend churn |
| VII. Linter & Safety | ✅ Pass (target) | Biome must stay clean; no type errors introduced |

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-dashboard-cryptix-redesign/
├── spec.md               # Feature specification
├── plan.md               # This file
├── research.md           # Phase 0: token/reference decisions
├── quickstart.md         # Phase 1: browser verification guide
├── checklists/
│   └── requirements.md   # Spec quality checklist
└── tasks.md              # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
dashboard/
├── src/
│   ├── index.css              # NEW: centralized Cryptix-inspired design tokens (:root vars)
│   ├── Dashboard.tsx          # US1: portfolio shell restyle
│   ├── StatCard.tsx           # US1: stat card restyle
│   ├── EquityChart.tsx        # US1: chart container/states restyle
│   ├── browse/
│   │   ├── BrowseStrategies.tsx   # US2: grid + filters shell
│   │   ├── FiltersBar.tsx         # US2
│   │   ├── StrategyCard.tsx       # US2
│   │   ├── Sparkline.tsx          # US2
│   │   ├── BacktestRunner.tsx     # US2
│   │   ├── AgentAnalysisCard.tsx  # US2
│   │   ├── BacktestReport.tsx     # US2 (route /backtest/:id)
│   │   └── AnalyzePage.tsx        # US2 (route /analyze)
│   └── main.tsx               # UNCHANGED (routes preserved)
└── (tests)                   # UNCHANGED in structure; must stay green
```

**Structure Decision**: Single frontend project (no new directories). Restyle in
place; keep `main.tsx` routing and all component file locations. The only new
artifact is the token block in `index.css`; everything else is class/CSS
refactor against those tokens.

## Phase 0 — Research (design reference resolution)

The Cryptix reference could not be fully inspected (Framer fetch returned only
title metadata). Per the spec's documented default, the redesign targets the
*modern Framer SaaS design language* genre. `research.md` records the concrete
token decisions (palette, radius, spacing, typography, shadows) as adjustable
defaults derived from that genre + the project's existing component inventory.

## Phase 1 — Design & Contracts

### Data Model

No new data entities. The feature consumes existing front-end types
(`EquityPoint`, `PortfolioStats`, `DashboardState`, `Strategy`) unchanged.
`data-model.md` is therefore N/A — documented here rather than created as a stub.

### Interface Contracts

No API contract changes. The redesign consumes the existing endpoints
(`/equity`, `/api/strategies`, `/api/backtest`, `/api/reflections`, `/api/stats`)
unchanged. `contracts/` is N/A (purely internal presentation change). Vite proxy
config (`/api`, `/equity` → :8000) is preserved.

### Quickstart Validation

`quickstart.md` documents the browser-based end-to-end verification:
1. `cd dashboard && npm install` (if needed) then `npm run dev` (Vite on :5173, proxying API).
2. Open `/` → confirm portfolio equity, P&L, drawdown, equity curve render in new theme.
3. Open Browse → apply a filter, open a strategy card, run a backtest, read agent analysis.
4. `npm run test` (Vitest) and `npm run lint` (Biome) must pass.
5. Optional: Playwright smoke of the primary journey.

### Agent context

`AGENTS.md` (if present) updated with a pointer to this plan between SPECKIT
markers; otherwise skipped.

## Implementation Strategy

MVP = US1 (Dashboard shell + tokens) — independently verifiable in browser and
the most visible win. US2 (Browse restyle) follows, reusing the same token set.
Polish = loading/empty/error states + Biome/type check + constitution restore.
Execute on branch `feature/dashboard-cryptix-redesign` (separate from
`feature/constitution-compliance`).

## Risks

- **Token inference**: Exact Cryptix palette/fonts unknown → tokens are documented
  defaults, adjustable in implementation. Mitigated by centralizing them (FR-008)
  so changes are single-point.
- **Test breakage**: Restyle must not break Vitest/Playwright selectors. Mitigated
  by keeping component structure/roles; only class names + CSS change.
- **Mixed aesthetics**: Risk of half-migrated UI. Mitigated by FR-003 (single token
  source) and a final cross-surface review in Polish.
