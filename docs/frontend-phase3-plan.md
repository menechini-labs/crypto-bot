# Phase 3 Plan — Trade Desk (paper)

Companion to `frontend-daytrader-architecture.md` + Phase 0/1/2 plans.
Goal: simulated trade execution surface (paper-only) with positions, risk-gated
orders, SL/TP + trailing stop, mark-to-market PnL. No real money, no auth.

**STATUS: DONE (2026-07-17)** — `core/paper_engine.py` + `core/market.fetch_ticker/fetch_depth`
+ `/api/positions` + `/api/orders`; frontend `TradeDesk.tsx` (tab Trade Desk).

## Binance public API reference (no-auth, free-tier)
From https://publicapis.io/binance-api (links official `binance-official-api-docs`):
- `GET /api/v3/ticker/price?symbol=BTCUSDT` — last price (used for paper fill + mark).
- `GET /api/v3/ticker/24hr` — 24h change/high/low/volume (used by `fetch_ticker`).
- `GET /api/v3/depth?symbol=BTCUSDT&limit=N` — order book (used by `fetch_depth`).
- `GET /api/v3/klines` — OHLCV (already used for closes).
- `GET /api/v3/exchangeInfo` — symbol filters (lot size/min notional; future validation).

## Backend
- `core/market.py`: added `fetch_ticker(symbol)` (price + 24h stats) and `fetch_depth(symbol, limit)`.
- `core/paper_engine.py` (NEW): `PaperEngine` singleton.
  - `submit(Order)` → risk gate (RiskManager.max_notional), idempotent order id,
    instant market fill at live ticker, SL/TP computed from pct, single long per symbol (MVP).
  - `check_exits()` → evaluates SL/TP + trailing stop, auto-submits closing sell.
  - `snapshot()` → cash, equity (mark-to-market), positions, counts.
- `core/strategy_api.py`: `GET /api/positions` (snapshot + check_exits), `POST /api/orders` (submit).

## Frontend
- `TradeDesk.tsx` (NEW): summary (cash/equity/positions/orders), order form
  (symbol/qty/SL/TP/trailing), BUY/SELL paper buttons, exits log, positions table (uPNL).
- `Dashboard.tsx`: tab `tradedesk`. `index.css`: +.trade-desk rules.

## Validação
- Engine unit check: buy fills at live price, dup-long rejected, sell closes, equity correct.
- `npm run build` passa.

## Notas / próximos
- Phase 4 (Polish): unified sidebar, paper/live toggle (paper-locked), connection status, a11y.
- `exchangeInfo` validation (lot size) — fase futura; MVP confia no qty do usuário.
- Positions in-memory (reset on restart) — ledger persistence é fase futura.
- `external_sources.py` (mcp-api.trader.dev) ainda não integrado.
