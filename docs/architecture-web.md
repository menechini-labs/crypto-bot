# Frontend Architecture — crypto-bot

## Part: `web` (React 18 + Vite + TypeScript)

Entry point: `dashboard/src/main.tsx`. Built output `dashboard/dist/` is served by
the FastAPI backend as static files.

## Executive Summary

"Signal Terminal" — a quant-style monitoring dashboard. Consumes the backend REST
API over HTTP (`fetch`). No backend business logic in the frontend; it is a thin
client that renders scores, backtests, and strategy浏览.

## Technology Stack

- React 18
- Vite (build/dev server)
- TypeScript
- Custom CSS design system (`index.css`): Syne display + JetBrains Mono data,
  signal accents (`--sig-ok`, `--sig-warn`, `--sig-rej`), grid + grain texture.

## Architecture Pattern

Component tree, data-fetching via `fetch` to `/api/*`:

```
Dashboard (shell + tabs)
├── ScorePanel       # score + LLM signal; SVG arc gauge, segment bars
├── StatCard         # KPI card (corner ticks)
├── EquityChart      # equity curve
└── browse/          # strategy cards, filters, sparklines
```

## Component Overview

| Component | Role |
|-----------|------|
| `Dashboard.tsx` | App shell, tab navigation, mono-glow headers |
| `ScorePanel.tsx` | Signal Terminal score UI; `runScore` (/api/score), `runLLM` (/api/llm-signal); EXECUTAR stamp when `conf>=0.4 && risk>=0.5` |
| `StatCard.tsx` | KPI metric card with corner tick |
| `EquityChart.tsx` | Equity curve rendering |
| `browse/StrategyCard.tsx` | Strategy metadata card (sym/tf/by chips) |
| `types.ts` | Shared TS types matching API JSON shapes |
| `index.css` | Signal Terminal design tokens + component classes |

## Data Flow

1. User interacts → component calls `fetch('/api/...')`.
2. Backend returns JSON (score, signal, backtest result).
3. Component renders via design-system classes (`.sig`, `.kpi`, `.bt-kpis`).

## Build / Dev

See [development-guide.md](development-guide.md). Build emits `dashboard/dist/`
which the backend serves — **frontend changes require `npm run build` to appear
in the served bundle.**

## Testing

- Vitest specs in `dashboard/src/__tests__` (7 passing).
- Note: `NODE_ENV=production` + `npm omit=dev` skips devDeps; use
  `npm install --include=dev` before `npm run build` / `vitest`.
