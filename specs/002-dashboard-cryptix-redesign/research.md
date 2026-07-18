# Research: Dashboard Cryptix Redesign

**Feature**: 002-dashboard-cryptix-redesign
**Date**: 2026-07-17

## Unknown: Cryptix template's actual visual design

### Decision
Adopt the **modern Framer SaaS design language** genre as the target aesthetic,
expressed through a concrete, centralizable token set (see below). Exact Cryptix
brand palette/fonts are **unknown** (Framer fetch returned only the title
"Cryptix: Free SaaS Website Template by Arthur Duchesne"; Dribbble reference was
unfetchable). Tokens are documented defaults, adjustable in implementation
without touching components (FR-008).

### Rationale
- The user pointed at Cryptix to "improve the frontend." Blocking the whole
  pipeline on an un-inspectable reference is worse than proceeding with a faithful
  genre default and keeping tokens swappable.
- Centralizing tokens means a future exact-Cryptix palette drop-in is a one-file
  change.

### Alternatives considered
- **Keep current retro-futurist terminal theme** (bg `#0a0c10`, amber `#f59e0b`,
  DM Mono, grid overlay). Rejected per spec US intent (modernize toward Cryptix).
  Carried as the open note in spec.md (default = replace).
- **Wait for user to paste exact tokens**. Rejected — spec already authorized
  proceeding with informed guesses.

## Unknown: Current frontend inventory (resolved by direct reading)

Grounded in actual files (not assumptions):

| File | Role | Current style hooks |
|------|------|---------------------|
| `dashboard/src/index.css` | Global theme: `--bg #0a0c10`, `--panel`, `--accent #f59e0b`, `--green #10b981`, `--red`, DM Mono, grid overlay, `.stat-card`, `.equity` | Single source of truth already (good) |
| `Dashboard.tsx` | Tabs (Overview/Positions), equity fetch, StatCard grid, EquityChart, reflections | uses `.stat-card`, `.tab`, `.panel` |
| `StatCard.tsx` | label/value/▲▼ delta | `.stat-card`, color via inline/class |
| `EquityChart.tsx` | Pure-SVG area chart, `.line-positive/.negative`, `.empty` | themed via classes |
| `browse/BrowseStrategies.tsx` | grid + filters + BacktestRunner, INIT_FILTERS | `.grid`, card links |
| `browse/FiltersBar.tsx` | filter inputs | `.filter-bar` |
| `browse/StrategyCard.tsx` | strategy card | `.card` |
| `browse/Sparkline.tsx` | tiny SVG sparkline | `.sparkline` |
| `browse/BacktestRunner.tsx` | run backtest form | `.runner` |
| `browse/AgentAnalysisCard.tsx` | LLM analysis block | `.analysis` |
| `browse/BacktestReport.tsx` | `/backtest/:id` report | `.report` |
| `browse/AnalyzePage.tsx` | `/analyze` | `.analyze` |
| `main.tsx` | Routes: `/`, `/backtest/:id`, `/analyze` | **must stay unchanged** |

Conclusion: One token source already exists (`index.css :root`). The redesign is a
**token + class refactor** against that single source — low risk, no backend.

## Unknown: Build/test tooling (resolved)

- Build: Vite. Dev: `npm run dev` (proxy `/api`, `/equity` → :8000).
- Lint/format: **Biome** (not ESLint/Prettier) — confirmed existing config.
- Tests: Vitest + Testing Library; e2e Playwright (`dashboard/test-results/`
  exists as stray dir). Restyle must keep these green (FR-007).

## Token Decision (Cryptix-inspired defaults)

```
--bg:          #0b0e14 (deep near-black, slightly bluer than current)
--panel:       #131822 (card surface)
--panel-2:     #1b2230 (raised/inner)
--border:      #232b39
--text:        #e7ecf3
--muted:       #8b97a8
--accent:      #6ea8fe (cool blue → replaces amber terminal accent)
--accent-2:    #7c5cff (violet secondary)
--green:       #34d399
--red:         #f87171
--radius:      14px
--radius-sm:   10px
--shadow:      0 8px 30px rgba(0,0,0,.35)
--font:        "Inter", system-ui, -apple-system, "Segoe UI", sans-serif
--font-mono:   "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace
--space:       8px base scale
```
Drop the grid overlay and DM Mono body; keep mono only for numeric/code. Soft
shadows, rounded cards, clear hierarchy. (Adjustable when exact Cryptix tokens
arrive.)
