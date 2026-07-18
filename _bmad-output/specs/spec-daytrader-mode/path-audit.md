# Path Audit — demo/real behavior per module

Companion to SPEC-daytrader-mode. Every load-bearing path in the project and how it behaves under each mode.

## Backend (`core/`)

| Path | DEMO | REAL |
|---|---|---|
| `market.py` (fetch_ohlcv, fetch_ticker, fetch_depth) | ✅ Live Binance data | ✅ Same — no change |
| `market_ws.py` | ✅ WebSocket streaming (startup-only) | ✅ Same |
| `strategy.py` (decide) | ✅ Signals computed | ✅ Same |
| `strategy_registry/*.py` (8 strategies) | ✅ All registered, all compute | ✅ Same |
| `scoring.py` | ✅ Score evaluation | ✅ Same |
| `indicators.py` | ✅ All indicator calcs | ✅ Same |
| `backtest.py` | ✅ Runs normally | ✅ Same |
| `news.py` (RSS CoinDesk+Cointelegraph) | ✅ Fetches and returns | ✅ Same |
| `agent_desk.py` (5-agent loop) | ✅ Cycles, reads live data | ✅ Same |
| `regime.py` | ✅ Regime detection | ✅ Same |
| `risk.py` (RiskManager) | ✅ Risk gates computed | ✅ Same — gates enforced |
| `paper_engine.py` (PaperEngine) | ❌ Not called. /api/orders returns error. Positions empty. | ✅ Full paper execution fill at live ticker |
| `execution.py` (PaperExecutor mode) | ❌ Not reachable | ✅ mode="live" gated by ALLOW_LIVE_TRADING=1 |
| `strategy_api.py` (FastAPI app) | ✅ /api/* all active. /api/orders blocked. /api/health returns mode=demo | ✅ Full API including /api/orders and /api/positions |
| `wallet.py` | ✅ Read-only | ✅ Paper wallet active |
| `config_loader.py` | ✅ Reads config | ✅ Same |
| `reflection.py` | ✅ Reflection system | ✅ Same |
| `dashboard.py` (legacy) | ✅ Static dashboard | ✅ Same |
| `reporter.py` | ✅ Reports | ✅ Same |
| `synth.py` | ✅ Synthetic data | ✅ Same |
| `metrics.py` | ✅ Metric collection | ✅ Same |
| `external_sources.py` | ✅ External URLs | ✅ Same |
| `cli.py` | ✅ run_cycle works | ✅ Same (no exec if DEMO) |
| `agent_analyzer.py` | ✅ Agent analysis | ✅ Same |

## Frontend (`dashboard/src/`)

| Path | DEMO | REAL |
|---|---|---|
| `Dashboard.tsx` | Sidebar shows DEMO badge. Mode state propagates to children. | Sidebar shows REAL badge. Same layout. |
| `TradeDesk.tsx` | Buy/sell buttons disabled. Text "DEMO mode — execution desligado". | Buttons active. Full order form. |
| `BrowseStrategies.tsx` | ✅ All strategies shown | ✅ Same |
| `ScorePanel.tsx` | ✅ Scoring interface | ✅ Same |
| `AnalyzePage.tsx` | ✅ Backtest runner | ✅ Same |
| `BacktestRunner.tsx` | ✅ Runs backtests | ✅ Same |
| `AgentDesk.tsx` | ✅ Agent cycle view | ✅ Same |
| `NewsFeed.tsx` | ✅ News feed | ✅ Same |
| `HealthPanel.tsx` | ✅ Health display | ✅ Same |
| `EquityChart.tsx` | Shows historical equity | ✅ Same — updates live |
| `index.css` | Mode class on root (`mode-demo` / `mode-real`) | Same |
| `api.ts` | Same fetch() calls | Same |
| `types.ts` | Mode type added | Same |

## Config

| Path | DEMO | REAL |
|---|---|---|
| `.env` | `MODE=demo` | `MODE=real` + `ALLOW_LIVE_TRADING=1` |
| `config.yaml` | mode field optional | mode field read at startup |
| `docker-compose.yml` | Single container | Same — env var changes only |

## Key architectural flow

```
Frontend (mode state)
  ↓
/api/orders (strategy_api.py)
  → if DEMO: {"ok": false, "error": "demo mode — no execution"}
  → if REAL: PaperEngine.submit() → fill at Binance live price → RiskManager gate
  ↓
/api/positions
  → DEMO: {"cash": 0, "equity": 0, "positions": [], "paper_only": true}
  → REAL: PaperEngine.snapshot() with real mark prices
  ↓
/api/health
  → DEMO: {"mode": "demo", "online": true, ...}
  → REAL: {"mode": "real", "online": true, ...}
```
