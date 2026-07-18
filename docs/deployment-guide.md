# Deployment Guide — crypto-bot

## Container (recommended)

`docker-compose.yml` builds the backend and (optionally) builds the dashboard,
then serves everything from the FastAPI container on `:8000`.

```bash
docker compose up --build
# backend API + dashboard at http://localhost:8000
```

- `Dockerfile` — Python backend, installs requirements, runs `run_api.py`.
- The image expects a pre-built `dashboard/dist/` (build it before compose, or
  add a build stage). See `docker-compose.yml` for the configured stages.

## Environment

| Var | Purpose |
|-----|---------|
| `ENABLE_LLM` | `1` to enable LLM strategy |
| `LLM_API_KEY` | Provider key (kept in `.env`, not committed) |
| `PORT` | Override listen port (default 8000) |

## Requirements

- No real exchange credentials needed (paper trading, public Binance data).
- Outbound HTTPS to Binance + LLM provider (if `ENABLE_LLM=1`).

## CI/CD

- No pipeline defined in repo yet. Tests: `pytest` (backend) + `vitest` (frontend).
- Recommended gate before merge: both test suites green + `npm run build` succeeds.

## Notes

- Paper only — safe to run in any environment; it never places real orders.
- Restart required for config/env changes (process reads env at startup).
