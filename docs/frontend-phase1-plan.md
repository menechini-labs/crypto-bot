# Phase 1 Plan — Markets & Signals Tabs

**STATUS: DONE (2026-07-17)** — backend endpoints live in `966e235`; frontend tabs Markets/Signals
are pending UI wiring (see note below). Core APIs ready: `/api/market/closes`, `/api/market/overview`,
`/api/indicators`, `/api/indices`, `/api/signals`. ScorePanel already consumes `/api/market/closes`
("BTCUSDT real" button) and `/api/score`.

Companion to `frontend-daytrader-architecture.md` + `frontend-phase0-plan.md`.
Builds on Phase 0 endpoints (`/api/market/closes`, `/api/market/overview`, live scoring).
Goal: two real tabs — Markets (watchlist + indicators) and Signals (live scored feed).
Constraint: paper-only, Binance public data, stdlib reuse, no heavy deps.

---

## 1.1 Backend: indicators endpoint (reuse `core/indicators.py`)

`core/strategy_api.py` — add `GET /api/indicators`:
```
GET /api/indicators?symbol=BTCUSDT&tf=1h&limit=100
```
Implementation:
- `candles = market.fetch_ohlcv(symbol, tf, limit)` (stdlib, public Binance).
- `closes = [c["close"] for c in candles]`.
- Compute with `core.indicators`:
  `rsi=indicators.rsi(closes), macd=indicators.mACD(closes), bb=indicators.bollinger(closes), sma_fast=indicators.sma(closes,5), sma_slow=indicators.sma(closes,20), ma_cross=indicators.ma_cross(closes)`.
- Return `{symbol, tf, rsi, macd:{macd,signal,hist}, bollinger:{mid,upper,lower}, sma_fast, sma_slow, ma_cross, last_close, ts}`.
- Cache 5s (same cache as `/api/market/closes`).
- Guard: if `len(closes) < 27` return 422 "insufficient data".

Reuse (do NOT rewrite): `core/market.fetch_ohlcv`, `core/indicators.{rsi,macd,bollinger,sma,ma_cross}`.

---

## 1.2 Backend: indices endpoint (market context)

`GET /api/indices`:
- BTC dominance: `GET https://api.coingecko.com/api/v3/global` → `data.market_cap_percentage.btc` (public, no key). Cache 60s.
- Fear & Greed: `GET https://api.alternative.me/fng/?limit=1` → `data[0].value` + `data[0].classification`. Cache 5min.
- Altseason index (optional): derive from dominance (if btc_dom < 50 → altseason bias).
- Return `{btc_dominance, fear_greed_value, fear_greed_label, altseason_bias, ts}`.
- On fetch failure: return last cached or `{"error":"unreachable"}` with 200 + stale flag (don't 500 the UI).

Note: CoinGecko/alternative.me are free, no-auth. OK per constraints. If either blocked, degrade gracefully.

---

## 1.3 Backend: live signals feed (WS + REST fallback)

Option A (preferred): `WS /ws/signals`.
- Server side: every 30s, for a watchlist (BTCUSDT, ETHUSDT, SOLUSDT), fetch closes, call `scoring.score_signal` per (symbol, tf), push JSON.
- Use `fastapi.WebSocket`; broadcast to subscribers.
- Payload per signal: `{symbol, tf, score, confidence, risk, verdict, regime, rsi, ma_cross, ts}`.

Option B (simpler, P1 MVP): `GET /api/signals?symbols=...&tf=1h`.
- Loop symbols, reuse `/api/indicators` + `scoring.score_signal`, return array.
- Frontend polls every 30s. (WS can come in P2/P3 if needed.)

Recommend **Option B for P1** (no WS infra yet); note WS in architecture for later.

---

## 1.4 Frontend: Markets tab

New file `dashboard/src/markets/MarketsPage.tsx` + `dashboard/src/markets/api.ts` + `types.ts` (or extend `browse/types.ts`).
- On mount + every 30s: `GET /api/market/overview?symbols=...` → watchlist rows: symbol, last price, 24h %, sparkline (from `/api/market/closes` mini).
- Click row → drawer/panel: `GET /api/indicators?symbol=&tf=` → show RSI (gauge), MACD bars, Bollinger band position, MA cross badge.
- `GET /api/indices` → top strip: BTC dominance, Fear&Greed pill (color by value), altseason bias.
- Reuse existing `Sparkline.tsx` for mini charts.
- Use `StatCard.tsx` style for indicator tiles.

Wire into nav: add `Markets` to sidebar (from architecture P0 Layout rail) → route `/markets`.

---

## 1.5 Frontend: Signals tab

New file `dashboard/src/signals/SignalsPage.tsx` + `api.ts`.
- Poll `GET /api/signals?symbols=...&tf=1h` every 30s.
- Render rows: symbol · tf · verdict badge (BUY/SELL/HOLD from `verdict`) · score arc (reuse `ScorePanel` gauge component, extract `<ScoreGauge score=.. />` from ScorePanel) · confidence/risk bars · regime chip · RSI.
- Click row → open Signal Terminal (ScorePanel) pre-filled with that symbol/tf (real closes), showing full `reasons`.
- "Usar LLM" button per row → `POST /api/llm-signal` with that symbol's closes; show LLM verdict inline.

Refactor: extract `ScoreGauge` + `SegmentBar` from `ScorePanel.tsx` into `dashboard/src/components/` so Signals + ScorePanel share visuals.

---

## 1.6 Shared component extraction

From `ScorePanel.tsx`:
- Move `ScoreGauge` (SVG arc) → `dashboard/src/components/ScoreGauge.tsx`.
- Move `SegmentBar` → `dashboard/src/components/SegmentBar.tsx`.
- `ScorePanel` imports them; Signals tab imports `ScoreGauge`.
Keep visual identity (Signal Terminal design tokens in `index.css`).

---

## 1.7 Tests

`tests/unit/test_strategy_api.py` extend:
- `/api/indicators` returns rsi/macd/bollinger/ma_cross for valid symbol; 422 for tiny limit.
- `/api/indices` returns object (or stale flag) without 500.
- `/api/signals` returns array with verdict+score.
Run via `.venv` + uv pytest.

## 1.8 Commit
Branch `feature/daytrader-phase1` (or continue `feature/daytrader-phase0` squashed).
Message (EN): `feat: phase1 markets+signals tabs (live indicators, indices, scored feed)`.

---

## Dependencies / reuse summary
- Backend: `core/market.fetch_ohlcv`, `core/indicators.*`, `core/scoring.score_signal`, `core/scoring.detect_regime`.
- External (free, no-auth): Binance klines/ticker, CoinGecko `/global`, alternative.me FNG.
- Frontend: existing `Sparkline`, `StatCard`, extracted `ScoreGauge`/`SegmentBar`, `index.css` tokens.
- No new npm deps required.
