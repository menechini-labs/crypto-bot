# Backend Architecture — crypto-bot

## Part: `backend` (Python 3.11+, FastAPI, stdlib-first)

Entry point: `run_api.py` → `uvicorn core.strategy_api:app --host 0.0.0.0 --port 8000`.

## Executive Summary

Deterministic trading engine with optional LLM strategy, composite signal scoring,
risk guards, paper execution, and a backtest engine. Exposes a FastAPI service that
also serves the built React dashboard.

## Technology Stack

- Python 3.11+
- FastAPI + Uvicorn
- stdlib for core logic (indicators, scoring, backtest)
- `urllib` for LLM HTTP client (no `requests`)
- ccxt / pandas / numpy for backtest data (dev deps)

## Architecture Pattern

Layered + plugin registry:

```
market (Binance) → indicators → strategy_registry → scoring → risk → execution/wallet
                                                  ↘ backtest (offline)
                                       reflection (post-trade analysis)
```

## Core Modules (roles)

| Module | Responsibility |
|--------|----------------|
| `market.py` | Public Binance REST klines/ticker (no auth) |
| `market_ws.py` | Public Binance WebSocket stream |
| `indicators.py` | RSI, volatility (stdlib) |
| `scoring.py` | `score_signal`, `SignalScore`, regime weights, SR/RSI |
| `strategy.py` / `strategy_registry/` | Strategy interface + grid / dynamic-grid / LLM |
| `risk.py` | SL/TP, position guards, Block() limits |
| `backtest.py` | No-look-ahead engine; `use_scoring`, `strategy` params |
| `reflection.py` | Analyze closed trades → insights |
| `regime.py` | Market regime detection |
| `metrics.py` | Performance metrics |
| `reporter.py` | Equity/PnL JSON reporter |
| `wallet.py` | Paper wallet (USDT), never real exchange |
| `execution.py` | Paper order executor |
| `agent_analyzer.py` | Backtest result analysis |
| `strategy_api.py` | FastAPI: endpoints + static dashboard serve |

## Data Architecture

- **No database.** State is in-memory + JSON files (`data/`, `reporter` output).
- Paper wallet holds a fictional USDT balance.

## API Design

See [api-contracts.md](api-contracts.md). Key gates:
- `POST /api/score` → composite signal score; execute if `conf>=0.4 && risk>=0.5`.
- `POST /api/llm-signal` → LLM strategy; requires `ENABLE_LLM=1` + `LLM_API_KEY`.
- `POST /api/backtest` → accepts `strategy: "llm"` and `use_scoring`.

## Strategy Registry (plugin pattern)

`Strategy` base (`base.py`) → implement `decide(closes, has_position, ctx)`.
Register in `registry.py`. `LLMStrategy` uses `urllib` client, falls back to HOLD
when disabled or on error.

## Development Workflow

See [development-guide.md](development-guide.md).

## Testing Strategy

- `pytest` unit/integration in `tests/` (111 passing).
- Backtest determinism via `synth.py` (no network).
