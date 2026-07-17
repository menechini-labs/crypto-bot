# Tasks: Dashboard Cryptix Redesign

**For**: `specs/002-dashboard-cryptix-redesign/spec.md`
**Date**: 2026-07-17
**Branch**: `feature/dashboard-cryptix-redesign`

**Input**: Feature specification `specs/002-dashboard-cryptix-redesign/spec.md`, plan `plan.md`, research `research.md`, quickstart `quickstart.md`.

**Scope note**: Presentation-layer-only redesign. No backend, no new data models, no API contract changes, no new dependencies. `main.tsx` routes preserved. Existing Vitest/Playwright suites must stay green (FR-007) — verification tasks use those suites, no new test authoring. Design tokens centralized in `dashboard/src/index.css` (FR-008).

## Format

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

## Phase 1 — Setup

- [x] T001 Create branch `feature/dashboard-cryptix-redesign` from `develop` (gitflow; does not merge `feature/constitution-compliance` — independent feature)
- [x] T002 Verify dev environment: `cd dashboard && npm install` then `npm run dev` reaches `:5173` proxying `/api` and `/equity` to `:8000`; confirm current UI loads before changes (baseline screenshot optional)

## Phase 2 — Foundational (shared tokens)

- [x] T003 [P] Replace the retro-futurist token block in `dashboard/src/index.css` `:root` with the Cryptix-inspired token set from `research.md` (palette `--bg #0b0e14`, `--panel #131822`, `--panel-2 #1b2230`, `--border #232b39`, `--text #e7ecf3`, `--muted #8b97a8`, `--accent #6ea8fe`, `--accent-2 #7c5cff`, `--green #34d399`, `--red #f87171`, `--radius 14px`, `--radius-sm 10px`, `--shadow 0 8px 30px rgba(0,0,0,.35)`, `--font Inter stack`, `--font-mono JetBrains Mono stack`) and remove grid-overlay/DM-Mono-body styles
- [x] T004 [P] Add base layer in `dashboard/src/index.css`: body background using `--bg`/`--panel`, Inter font, reset for `.panel`/`.card` to use `--radius`/`--shadow`/`--border` so all existing components inherit the new theme with no per-component edits yet

## Phase 3 — User Story 1: Modernized dashboard landing (P1)

**Goal**: The `/` Dashboard renders the portfolio (equity, P&L, drawdown, win-rate) and equity curve in the new Cryptix theme, all data preserved.

**Independent test criteria**: `npm run dev` → `/` shows stat cards (rounded, soft shadow, blue accent) + equity curve with positive/negative coloring + reflections; no console errors; all previously displayed data present (SC-001).

- [x] T005 [US1] Restyle `dashboard/src/StatCard.tsx` to consume tokens: `.stat-card` uses `--panel`/`--radius`/`--shadow`/`--border`, label `--muted`, value `--text`, delta colors `--green`/`--red`; keep ▲▼ semantics
- [x] T006 [US1] Restyle `dashboard/src/Dashboard.tsx`: tab bar (`.tab`, active state with `--accent`), stat-grid spacing via `--space` scale, `.panel` surfaces; preserve Overview/Positions tabs and data wiring
- [x] T007 [US1] Restyle `dashboard/src/EquityChart.tsx`: `.line-positive`/`.line-negative` use `--green`/`--red`, `.empty` uses new `--muted`/panel style; chart container card uses token radius/shadow
- [x] T008 [US1] Verify US1 in browser per `quickstart.md` S1; run `npm run lint` (Biome) and `npm run test` (Vitest) — must stay green

## Phase 4 — User Story 2: Redesigned strategy browse & analysis (P2)

**Goal**: Browse + analysis surfaces restyled in the same theme; all current capabilities preserved.

**Independent test criteria**: Browse grid, filters, strategy cards w/ sparklines, backtest runner, agent-analysis render in new theme; filter + backtest + analysis journeys complete; token source still single (SC-002); tests green (SC-003).

- [x] T009 [P] [US2] Restyle `dashboard/src/browse/BrowseStrategies.tsx`: grid + `.grid` spacing via `--space`, page header/section spacing, keep `INIT_FILTERS` and data fetch
- [x] T010 [P] [US2] Restyle `dashboard/src/browse/FiltersBar.tsx`: inputs/selects use `--panel-2`/`--border`/`--radius-sm`/`--text`, focus ring `--accent`
- [x] T011 [P] [US2] Restyle `dashboard/src/browse/StrategyCard.tsx`: `.card` uses token radius/shadow/border, title `--text`, metrics `--muted`, hover lift; preserve Link to detail
- [x] T012 [P] [US2] Restyle `dashboard/src/browse/Sparkline.tsx`: stroke uses `--accent`/`--green`/`--red` per series; container consistent
- [x] T013 [P] [US2] Restyle `dashboard/src/browse/BacktestRunner.tsx`: form/button use tokens, primary action `--accent`, disabled state muted
- [x] T014 [P] [US2] Restyle `dashboard/src/browse/AgentAnalysisCard.tsx`: `.analysis` block uses panel/radius/border, code/mono spans use `--font-mono` + `--muted`
- [x] T015 [P] [US2] Restyle `dashboard/src/browse/BacktestReport.tsx` (`/backtest/:id`): report layout + tables use tokens, numeric coloring preserved
- [x] T016 [P] [US2] Restyle `dashboard/src/browse/AnalyzePage.tsx` (`/analyze`): page shell + controls use tokens
- [x] T017 [US2] Verify US2 in browser per `quickstart.md` S2; run `npm run lint` and `npm run test` — must stay green (SC-003)

## Phase 5 — Polish & Cross-Cutting

- [x] T018 Restyle loading/empty/error states across surfaces to use new tokens (FR-005): e.g. Dashboard loading/error, Browse empty grid, BacktestRunner idle
- [x] T019 [P] Responsive pass (FR-006): confirm stat-grid and Browse grid use flexible/grid min-widths that degrade gracefully at narrow widths; no fixed breakage
- [x] T020 [P] Restore `.specify/memory/constitution.md` v1.0.0 (wiped earlier) so governance artifacts persist; confirm `.specify/feature.json` points to `specs/002-dashboard-cryptix-redesign`
- [x] T021 Cross-surface review (SC-002): grep `dashboard/src` for hard-coded colors/hex/shadow outside `index.css :root`; ensure single token source, no conflicting duplicates
- [x] T022 Final verification: `npm run lint` + `npm run test` green; `npm run dev` → walk S1–S4 in `quickstart.md`; capture confirmation that primary journey (view portfolio → Browse → backtest → analysis) is fully in new theme (SC-004)

## Dependencies

- T001, T002 before all (env + branch)
- T003, T004 (Phase 2 tokens) block all US phases (T005–T017)
- US1 (T005–T008) independent of US2 (T009–T017) — parallelizable after Phase 2
- T018–T022 (Polish) after both stories

## Parallel Execution Examples

- Phase 2: T003 + T004 (different regions of same file — sequential-safe, marked [P] but edit same file; run together carefully)
- US1: T005, T006, T007, T008 are mostly sequential within one surface but T005/T007 can be parallelized
- US2: T009–T016 all touch different files → fully parallelizable [P]; T017 sequent after them
- Polish: T018, T019, T020 independent → parallelizable

## Implementation Strategy

MVP = US1 (T005–T008): independently verifiable Dashboard reskin, the highest-visibility win. Then US2 reuses the same token set. Polish (states/responsive/governance/review) last. Commit only when user requests (GitFlow branch kept; no auto-merge).
