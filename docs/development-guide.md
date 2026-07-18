# Development Guide — crypto-bot

## Prerequisites

- Python 3.11+
- Node 18+ (for dashboard)
- `uv` (recommended by BMAD; optional for this project — uses venv)
- Git

## Backend (Python)

```bash
# setup venv
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# run API (serves dashboard/dist at :8000)
python run_api.py
# or: uvicorn core.strategy_api:app --host 0.0.0.0 --port 8000

# CLI cycle
python cli.py run_cycle

# tests (pytest)
.venv/bin/python -m pytest
```

LLM enable (optional):
```bash
export ENABLE_LLM=1
export LLM_API_KEY=sk-...
```

## Frontend (React)

```bash
cd dashboard
# IMPORTANT: NODE_ENV=production + npm omit=dev skips devDeps.
# Use --include=dev so vitest/build tools install.
npm install --include=dev
npm run dev        # dev server
npm run build      # emits dashboard/dist/ (served by backend)
npx vitest run     # 7 tests
```

> Frontend changes only appear in the served bundle after `npm run build`.

## Config

- `config.yaml` — runtime (symbols, timeframes, risk params).
- `.env` / `.env.template` — secrets (LLM_API_KEY). Never commit real `.env`.

## Common Tasks

- Add a strategy: implement `Strategy` in `core/strategy_registry/`, register in `registry.py`.
- Adjust scoring: edit `core/scoring.py` (weights, `REGIME_WEIGHTS`).
- Update UI: edit `dashboard/src/*`, then `npm run build`.

## Testing Strategy

- Backend: `pytest` (unit + integration), 111 passing.
- Frontend: `vitest` (component), 7 passing.
- Backtest determinism via `core/synth.py` (no network).
