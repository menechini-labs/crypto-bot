# API Contracts — crypto-bot (FastAPI)

Base: served by `core/strategy_api.py` on `:8000`. CORS open for local dev.
Backend also serves `dashboard/dist/` as static at `/`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/strategies` | List registered strategies |
| GET | `/api/strategies/{id}` | Strategy detail |
| GET | `/api/strategies/{id}/fork.json` | Fork/export strategy config |
| GET | `/api/stats` | Runtime/portfolio stats |
| POST | `/api/score` | Composite signal score |
| POST | `/api/llm-signal` | LLM strategy signal |
| POST | `/api/backtest` | Run backtest |
| GET | `/api/backtest/{bt_id}` | Backtest result by id |
| POST | `/api/backtest/{bt_id}/reflection` | Attach reflection to backtest |
| GET | `/api/reflections` | List reflections |
| GET | `/download/project` | Download project bundle |
| GET | `/equity` | Equity data (JSON) |
| GET | `/` | Dashboard static (index.html) |
| GET | `/{full_path:path}` | Static asset fallback |

## Key Request/Response Shapes

### POST /api/score

Request:
```json
{ "closes": [float, ...],   // >= 20 samples
  "signal": "BUY" | "SELL" | "HOLD",
  "has_position": bool,
  "ctx": { } }              // optional context
```
Response (gated):
```json
{ "score": float, "confidence": float, "risk": float,
  "execute": bool,          // conf>=0.4 && risk>=0.5
  "explanation": "..." }
```

### POST /api/llm-signal

Request: `{ "closes": [...], "has_position": bool, "ctx": {} }`
Response:
```json
{ "status": "ok", "llm_enabled": bool,
  "signal": "BUY|SELL|HOLD", "score": float, "explanation": "..." }
```
Note: returns `llm_enabled:false` + HOLD fallback when `ENABLE_LLM!=1` or no `LLM_API_KEY`.

### POST /api/backtest

Request:
```json
{ "closes": [...], "symbol": "BTC/USDT",
  "strategy": "default" | "llm",
  "use_scoring": true }
```
Response: backtest result (trades, equity, metrics) with `bt_id`.

## Auth

- No auth on read/data paths.
- LLM path requires server-side `ENABLE_LLM=1` + `LLM_API_KEY` env.
