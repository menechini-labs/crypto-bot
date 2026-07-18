# Project Overview — crypto-bot

## Purpose

A paper-trading crypto bot for learning and strategy experimentation. Spot only,
zero real-funds risk. Combines deterministic rule-based strategies with an optional
LLM strategy, a composite **signal-scoring** gate, a no-look-ahead backtest engine,
walk-forward analysis, and a React "Signal Terminal" dashboard.

## Executive Summary

- **Market data:** Binance public REST/WebSocket (no auth for reads).
- **Strategies:** grid, dynamic-grid (deterministic) + LLM strategy (gated).
- **Scoring:** composite weighted signal score; rejects low-confidence / high-risk signals.
- **Risk:** SL/TP, position guards, paper wallet.
- **Backtest:** stdlib engine, optional walk-forward; supports `strategy="llm"`.
- **Dashboard:** React Signal Terminal consuming `/api/score`, `/api/llm-signal`, `/api/backtest`.
- **Serve:** FastAPI backend also serves the built `dashboard/dist/` as static files.

## Technology Stack

| Category | Technology | Notes |
|----------|-----------|-------|
| Language (backend) | Python 3.11+ | stdlib-first |
| API framework | FastAPI + Uvicorn | `core/strategy_api.py` |
| Data | Binance public REST/WS | `core/market.py`, `core/market_ws.py` |
| Strategy registry | Python modules | `core/strategy_registry/` |
| Scoring | stdlib | `core/scoring.py` |
| Frontend | React 18 + Vite + TS | `dashboard/` |
| Styling | Custom CSS (Signal Terminal design system) | `dashboard/src/index.css` |
| Container | Docker + docker-compose | `Dockerfile`, `docker-compose.yml` |
| Tests | pytest + vitest | `tests/`, `dashboard/src/__tests__` |

## Repository Structure

Multi-part: `core/` (backend engine + API) and `dashboard/` (frontend). See
[source-tree-analysis.md](source-tree-analysis.md).

## Links

- Backend architecture → [architecture-backend.md](architecture-backend.md)
- Frontend architecture → [architecture-web.md](architecture-web.md)
- Integration → [integration-architecture.md](integration-architecture.md)
- API → [api-contracts.md](api-contracts.md)
