---
title: "crypto-bot — Product Brief"
status: draft
created: 2026-07-17
updated: 2026-07-17
author: bmad-product-brief (headless)
source: BMAD Document Project output (docs/)
---

# crypto-bot — Product Brief

> Headless draft. Intent: **create**. Assumptions tagged `[ASSUMPTION]`. Grounded in `docs/` (DP output).

## 1. Why this exists
crypto-bot is a **paper-trading crypto signal/strategy engine** with a real-time web terminal. It already works end-to-end: public Binance data → scoring + strategy (incl. LLM) → FastAPI backend → React "Signal Terminal" frontend. The brief defines the **next horizon**: move from "working demo" to "dependable, observable, optionally autonomous" tool.

## 2. What it is (form-factor)
- **Backend:** Python (stdlib + FastAPI). No exchange auth, no real orders. Public Binance REST/WS only.
- **Frontend:** React + Vite + TypeScript single-page "Signal Terminal" (dashboard/dist served by backend).
- **Surface:** Web only (single webapp). `[ASSUMPTION]` No mobile/desktop planned this horizon.
- **Deployment:** Docker Compose, single container, port 8000.

## 3. Core capabilities (current)
- Multi-strategy registry: grid, dynamic-grid, LLM (`LLMStrategy`, stdlib `urllib` client, `ENABLE_LLM=1` + `LLM_API_KEY`).
- Composite scoring engine (`core/scoring.py`): SignalScore, regime-weighted, volatility/regime/SR/RSI, `should_execute` gate (confidence ≥ 0.4, risk ≥ 0.5).
- Risk guard with SL/TP.
- Backtest with walk-forward + `use_scoring` gate.
- API: 14 routes incl. `/api/score`, `/api/llm-signal`, `/api/backtest`.
- Streamlit dashboard for analytics.

## 4. Stakes & audience
- **Stakes:** Passion/learning project with real-market signal value. `[ASSUMPTION]` Not a funded product; no external investors yet.
- **Primary user:** Adilson (SRE, crypto/AI interested). Secondary: technical peers reviewing the terminal.
- **Risk posture:** Paper-only by design — safe to iterate aggressively.

## 5. Next-horizon goals (proposed)
1. **Reliability & observability** — local LLM fallback (llama.cpp) + alerting (Discord/SMTP) when LLM provider fails; structured run logs.
2. **Production-like validation** — calibrate scoring weights per regime on real historical data; expand backtest coverage.
3. **DX hardening** — `Makefile` targets, pinned `requirements.txt`, CI gate (pytest + vitest + `npm run build`).
4. **Autonomy (optional)** — scheduled continuous-cycle mode with safe guardrails. `[ASSUMPTION]` Out of scope for horizon 1.

## 6. Open questions
- Real-time WS path (`core/market_ws.py`) is currently orphan/unused — adopt, or drop? `[ASSUMPTION]` Defer; REST polling suffices for paper terminal.
- Which LLM provider is primary? (affects fallback design)
- Desired alerting channel: Discord vs email vs both?

## 7. Non-goals (this horizon)
- Real-money trading / exchange auth.
- Multi-asset portfolio management.
- Mobile app.

## 8. Success looks like
- `make test` green (backend + frontend) in CI.
- LLM signal path survives provider outage via local fallback + alert.
- Scoring weights documented and regime-calibrated.
- Terminal shows live signal + score + regime with one command (`docker compose up`).
