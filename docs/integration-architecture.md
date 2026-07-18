# Integration Architecture — crypto-bot

## How the parts connect

```
┌─────────────┐     HTTP /api/* (JSON)     ┌──────────────────┐
│  React UI   │ ──────────────────────────▶│  FastAPI backend │
│ (dashboard) │ ◀──────────────────────────│  (core/)         │
└─────────────┘     served static dist      └────────┬─────────┘
                                                      │
                                                      │ public REST/WS (no auth)
                                                      ▼
                                              ┌──────────────┐
                                              │  Binance     │
                                              │  (read-only) │
                                              └──────────────┘
```

## Integration Points

### 1. Frontend ↔ Backend (REST, JSON)

- Frontend is a **thin client**; no trading logic in React.
- `ScorePanel.runScore` → `POST /api/score` body `{closes[], signal, has_position, ctx?}`.
- `ScorePanel.runLLM` → `POST /api/llm-signal` body `{closes[], has_position, ctx?}`.
- Backtest view → `POST /api/backtest` (supports `strategy:"llm"`, `use_scoring`).
- Backend serves built `dashboard/dist/` at `/` (static).

### 2. Backend ↔ Binance (public, read-only)

- `core/market.py` — REST klines/ticker (no API key).
- `core/market_ws.py` — WebSocket ticker/stream.
- **No write path** — paper wallet only; `execution.py` never hits a live exchange.

### 3. Strategy ↔ Scoring ↔ Risk (internal)

```
indicators → strategy.decide() → score_signal() → risk guard → execute gate
                                   (conf>=0.4 & risk>=0.5)
```

### 4. Backtest (offline)

- `core/backtest.py` runs independently of live data; uses ccxt public klines or
  `synth.py` synthetic series. Supports walk-forward (rolling train/test).

## Shared Contracts

- TS `types.ts` mirrors API JSON shapes (score, signal, backtest result).
- Keep frontend types in sync when API response schema changes.
