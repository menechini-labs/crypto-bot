<p align="center">
  <img alt="CryptoBot" src="https://img.shields.io/badge/crypto--bot-paper%20trading-111418?style=for-the-badge&logo=bitcoin&logoColor=%23f59e0b" width="320px">
</p>

<h1 align="center">crypto-bot</h1>

<p align="center">
  <strong>A paper trading bot for cryptocurrency strategies — spot only, zero risk, full learning</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status"/>
  <img src="https://img.shields.io/badge/dependencies-stdlib%2B-orange" alt="Dependencies"/>
  <img src="https://img.shields.io/badge/tests-111%20passed-brightgreen" alt="Tests"/>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#installation--usage">Installation & Usage</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#strategies">Strategies</a> •
  <a href="#dashboard--api">Dashboard & API</a> •
  <a href="#risk--security">Risk & Security</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#running-tests">Running Tests</a> •
  <a href="#code-quality">Code Quality</a> •
  <a href="#specifications">Specifications</a>
</p>

---

## Overview

crypto-bot is a **paper trading bot** for cryptocurrency strategies — **spot only** (no leverage), using public market data from the Binance HTTP API. No exchange keys, no withdrawals, no live trading. Every trade is simulated in a fictional wallet.

The purpose is to **learn the system**: data collection, technical indicators, strategy logic, simulated portfolio, risk management, and performance metrics — without risking real capital. It is a laboratory for strategy development with instant visual feedback.

Built with a **stdlib-first** philosophy: core modules (indicators, backtest, config, HTTP server) use zero external dependencies. The frontend is a self-contained React SPA (Vite + TypeScript), and the unified API server runs on FastAPI.

### What's inside

| Feature | Description |
|---------|-------------|
| **Paper Wallet** | Fictional USDT wallet with fee simulation — no exchange interaction |
| **Market Data** | Public OHLCV from Binance REST API (no auth required) |
| **Technical Indicators** | SMA, EMA, RSI, MACD, Bollinger Bands (stdlib implementation) |
| **Strategies** | Grid (static & dynamic), Combined (multi-indicator), Baseline (MA-cross) |
| **Regime Detector** | Linear regression slope classifier — auto-selects strategy by market regime |
| **Backtest Engine** | Candle-by-candle simulation with zero look-ahead |
| **Risk Manager** | Stop-loss, take-profit, position sizing per trade |
| **Synthetic Series** | Deterministic price series (sideways/uptrend/downtrend) for controlled testing |
| **React Dashboard** | Live equity chart (SVG), stat cards, auto-refresh, strategy browser |
| **FastAPI + Frontend** | Unified server serving API endpoints and React SPA on a single port |
| **Agent Analysis** | Post-backtest reflection engine: trade patterns, insights, recommendations |
| **Safety Guards** | Double-locked executor: paper-only by default, live requires explicit env var |

## Features

### 📊 Paper Wallet & Execution

- **Fictional USDT wallet**: Buy/sell operations update local balances only — no network calls
- **Fee simulation**: Configurable taker fee (default 0.1%, Binance spot standard) deducted from every trade
- **Multi-symbol**: Supports simultaneous positions across different pairs (BTC, ETH, SOL, etc.)
- **Equity tracking**: Wallet handles position averaging, partial equity calculation, cycle counter

### 📈 Technical Indicators

All indicators implemented in pure Python (stdlib-only, no numpy/pandas dependency):

| Indicator | Function | Params |
|-----------|----------|--------|
| **SMA** | Simple Moving Average | configurable period |
| **EMA** | Exponential Moving Average | configurable period, smoothing factor |
| **RSI** | Relative Strength Index | 14-period default, arithmetic average |
| **MACD** | Moving Average Convergence Divergence | 12/26/9 default |
| **Bollinger Bands** | 20-period, 2 standard deviations | configurable period & k |
| **MA Cross** | Fast/slow SMA crossover signal | 5/20 default |

### 🧠 Strategy Layer

Four strategies ranging from baseline to multi-indicator:

- **Grid (static)**: Fixed price levels within a range — buy on dips, sell on rips. Best in sideways markets.
- **Grid Dynamic**: Recenters grid levels on the moving average — adapts to drift. Best in uptrends.
- **Combined**: MA-cross + RSI filter + MACD histogram + Bollinger Band proximity. Most selective.
- **Baseline**: Simple MA-cross with RSI guard. Lowest latency, lowest barrier to entry.

The **Regime Detector** (`core/regime.py`) classifies the last N candles using linear regression slope and auto-selects:
```
uptrend   → grid_dynamic
lateral   → grid (static)
downtrend → combined
```

### 🔬 Backtest Engine

- **Candle-by-candle** simulation — the decision at step `t` uses only `closes[0..t]` (zero look-ahead)
- **Deterministic**: Same parameters always produce the same result (no randomness in core loop)
- **Risk integration**: Stop-loss and take-profit checked before every new entry
- **Metrics output**: Sharpe ratio, CAGR, max drawdown, win rate, trade count
- **Reflection engine**: Post-backtest trade analysis with pattern detection, insights, and recommendations

### 🌐 Dashboard & API

- **React SPA** (Vite + TypeScript): Equity chart (pure SVG), stat cards, positions table, strategy browser
- **FastAPI unified server**: Serves API endpoints (`/api/strategies`, `/api/backtest`, `/api/stats`) + SPA static files + `/equity` on a single port
- **Auto-refresh**: Dashboard polls `/equity` every 5 seconds
- **Browse Strategies**: Mock data explorer with filtering by Sharpe, drawdown, win rate, symbol, author
- **Backtest Runner**: Run backtests from the UI, view reports with agent analysis

### 🛡️ Risk & Security

- **Paper-only by default**: `PaperExecutor(mode="paper")` — never sends a real order
- **Live requires double consent**: `mode="live"` needs `ALLOW_LIVE_TRADING=1` env var, and even then returns `LIVE_PENDING_REVIEW` (no actual network call)
- **Per-trade risk**: Configurable stop-loss (default 5%), take-profit (default 10%), max position size (default 50% of cash)
- **Network resilience**: Market data fetch failures log a warning and skip the cycle — never crash the loop
- **JSON corruption safety**: `reporter.py` gracefully handles corrupted equity files, restarting from empty state
- **No credentials stored**: Market data endpoint is hardcoded and public — zero API keys, zero secrets

## How It Works

crypto-bot runs in **cycles**. Each cycle is a self-contained decision loop with clear, observable stages:

```
1. LOAD      config.yaml → parameters (symbols, strategy, risk limits)
2. FETCH     Binance public REST API → latest OHLCV candles
3. COMPUTE   indicators (SMA/EMA/RSI/MACD/Bollinger) + regime classification
4. DECIDE    strategy selects BUY / SELL / HOLD using only past data (no look-ahead)
5. VALIDATE  risk manager checks stop-loss / take-profit / position size
6. EXECUTE   paper wallet applies fill + fee (no network call)
7. RECORD    reporter persists updated equity to data/equity.json
8. REFLECT   (backtest) agent analyzer classifies result + generates insights
```

The same loop powers both **live paper mode** (`--mode continuous`) and **backtest mode** (`/api/backtest`) — backtest simply feeds a synthetic or historical candle series instead of the live fetch. The dashboard reads the recorded equity history and renders it in real time.

## Architecture

### Data Flow

```
config.yaml
    ↓
config_loader.py  →  dict of parameters
    ↓
market.py (Binance public REST API)  →  OHLCV candles
    ↓
indicators.py  →  SMA, RSI, EMA, MACD, Bollinger
    ↓
regime.py → select_strategy()        strategy.py → decide_*()
    ↓
risk.py  →  validates stop-loss / take-profit / position size
    ↓
wallet.py  →  executes paper buy/sell (deducts fee)
    ↓
reporter.py  →  persists equity/PnL to data/equity.json
    ↓
dashboard / API  →  FastAPI serves data + React SPA on :8000
```

### Core Components

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `cli.py` | CLI entrypoint: once / continuous / report / dashboard | stdlib |
| `config_loader.py` | YAML config parser (stdlib split-based, no PyYAML) | stdlib |
| `market.py` | OHLCV fetch from Binance public API | urllib |
| `indicators.py` | SMA, EMA, RSI, MACD, Bollinger, MA-cross | stdlib |
| `strategy.py` | 4 decision strategies: grid, grid_dynamic, combined, baseline | indicators |
| `wallet.py` | Paper wallet: buy/sell with fees, position tracking | stdlib |
| `risk.py` | Stop-loss, take-profit, max position % | stdlib |
| `execution.py` | Paper executor: simulated fills, no network | stdlib |
| `backtest.py` | Candle-by-candle backtest engine | wallet, risk, metrics |
| `metrics.py` | Sharpe, CAGR, max drawdown, win rate | math |
| `reporter.py` | JSON persistence of equity history | json |
| `regime.py` | Market regime detector + strategy selector | stdlib |
| `synth.py` | Deterministic synthetic price series | math, random |
| `strategy_api.py` | FastAPI app: `/api/strategies`, `/api/backtest`, equity, static SPA | FastAPI |
| `agent_analyzer.py` | Backtest result classifier (ok/warn/alert) | stdlib |
| `reflection.py` | Post-backtest trade pattern analysis | json |

## Installation & Usage

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard development)

### Setup

```bash
# Clone the repository
git clone https://github.com/menechini-labs/crypto-bot.git
cd crypto-bot

# Install Python dependencies
pip install -e .                      # minimal (stdlib-only for core)
pip install 'uvicorn[standard]'        # for the unified FastAPI server

# Install & build frontend (optional)
cd dashboard
npm install
npm run build                          # production build -> dashboard/dist/
cd ..

# Run
python3 cli.py --mode once
```

### CLI Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Once** | `python3 cli.py --mode once` | Run a single decision cycle with real Binance data |
| **Continuous** | `python3 cli.py --mode continuous --interval 60` | Loop every N seconds, persisting equity history |
| **Dashboard** | `python3 cli.py --mode dashboard` | Start unified server: FastAPI + React SPA on `localhost:8000` |
| **Report** | `python3 cli.py --mode report` | Show last 10 equity records from `data/equity.json` |

### Options

```
--strategy grid|grid_dynamic|combined|default    Override config strategy
--interval N                                      Seconds between cycles (continuous mode)
```

### Development (Frontend)

```bash
cd dashboard
npm run dev          # Vite dev server on :5173 (proxies /api to :8000)

# In another terminal:
python3 run_api.py   # FastAPI server on :8000
```

## Configuration

```yaml
# config.yaml
exchange: binance          # data source
symbols:
  - BTC/USDT
  - ETH/USDT
timeframe: 1h              # candle interval (1m, 5m, 15m, 1h, 4h, 1d)
initial_cash_usdt: 1000.0  # starting paper balance
fee_pct: 0.001            # 0.1% taker fee (Binance spot)
max_position_pct: 0.5     # max 50% of cash in a single position
stop_loss_pct: 0.05       # 5% stop-loss
take_profit_pct: 0.10     # 10% take-profit target
lookback: 100             # candles for indicator calculation
strategy: grid            # grid | grid_dynamic | combined | default
```

## Strategies

### Grid (Static)

Divides a price range into N equally spaced levels. When price crosses a level downward, buy. When it crosses upward, sell. Best in **sideways / range-bound** markets.

```
Levels: [100, 125, 150, 175, 200]
Price 128 → drops to 118: crosses 125 → BUY
Price 128 → rises to 158: crosses 150 → SELL (if position held)
```

### Grid Dynamic

Same principle, but the center is recentered on each cycle using the current price. The grid "follows" the trend, making it suitable for **uptrends** while still operating in range-bound fashion.

### Combined

Multi-indicator filter. Only enters when **all** conditions align:
- **BUY**: MA-cross bullish AND RSI < 70 AND MACD histogram > 0 AND price ≤ upper Bollinger Band
- **SELL**: MA-cross bearish OR (price ≥ upper band AND MACD < 0)

Designed for **downtrends** — intentionally selective to reduce false entries.

### Regime Auto-Selector

The `regime.py` module classifies market conditions via linear regression slope on the last N closes:

| Slope | Regime | Strategy Selected |
|-------|--------|-------------------|
| `> +0.05%` per candle | **Uptrend** | `grid_dynamic` |
| `< -0.05%` per candle | **Downtrend** | `combined` |
| In between | **Lateral** | `grid` (static) |

## Dashboard & API

### API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/strategies` | List mock strategies with filters (symbol, timeframe, Sharpe, drawdown, etc.) |
| GET | `/api/strategies/{id}` | Single strategy detail |
| GET | `/api/strategies/{id}/fork.json` | Download strategy config as JSON |
| GET | `/api/stats` | Aggregate stats (total strategies, avg PnL/Sharpe) |
| POST | `/api/backtest` | Run synthetic backtest with configurable regime, strategy, candles, seed |
| GET | `/api/backtest/{id}` | Retrieve cached backtest report + analysis |
| POST | `/api/backtest/{id}/reflection` | Generate AI reflection on backtest trades |
| GET | `/api/reflections` | History of saved reflections |
| GET | `/equity` | Paper wallet equity history from `data/equity.json` |
| GET | `/docs` | Interactive API documentation (Swagger UI) |

### Frontend Pages

- **Dashboard**: Equity chart (SVG area), stat cards (equity, PnL, max drawdown), positions list. Auto-refreshes every 5s.
- **Browse Strategies**: Grid of strategy cards with filters by symbol, timeframe, Sharpe, win rate, drawdown. Sparkline preview per strategy.
- **Backtest Report**: Run synthetic backtests, view performance metrics, trigger agent reflection analysis.
- **Analysis**: Agent-generated assessment (ok/warn/alert) with trade pattern insights.

## Risk & Security

### Execution Safety

```python
# DEFAULT: paper only — never sends a real order
ex = PaperExecutor(mode="paper")

# LIVE requires EXPLICIT consent — two barriers:
# 1) Constructor checks ALLOW_LIVE_TRADING=1 env var
# 2) Even in live, returns LIVE_PENDING_REVIEW (no network call)
ex = PaperExecutor(mode="live")     # RuntimeError unless env var set
```

### Position Risk

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_position_pct` | 50% | Max fraction of cash allocated to one trade |
| `stop_loss_pct` | 5% | Automatic exit if price falls X% from entry |
| `take_profit_pct` | 10% | Automatic exit if price rises X% from entry |

Stop-loss and take-profit are evaluated **before** any new entry signal, preventing the bot from buying into a losing position in the same cycle.

### Security Tests

The project includes dedicated safety tests (`test_safety.py`, `test_execution.py`) that verify:
- Default mode is always `paper`
- Live mode is blocked without explicit `ALLOW_LIVE_TRADING=1` environment variable
- Paper buy/sell operations make zero network calls
- Backtest risk limits prevent runaway losses (stop-loss caps drawdown)

## Project Structure

```
crypto-bot/
├── cli.py                    # CLI entrypoint (once / continuous / report / dashboard)
├── run_api.py                # Standalone FastAPI launcher (uvicorn)
├── config.yaml               # Bot configuration
├── pyproject.toml            # Project metadata + tool configs
├── ruff.toml                 # Ruff linter configuration
├── .pre-commit-config.yaml   # Pre-commit hooks (ruff, pyright, vulture, safety)
├── requirements.txt          # Runtime dependencies
├── core/                     # Backend domain modules
│   ├── config_loader.py      # YAML config parser (stdlib)
│   ├── market.py             # OHLCV fetch from Binance public API
│   ├── indicators.py         # SMA, EMA, RSI, MACD, Bollinger
│   ├── strategy.py           # Grid, grid_dynamic, combined, baseline
│   ├── wallet.py             # Paper wallet (buy/sell simulation)
│   ├── risk.py               # Stop-loss, take-profit, position sizing
│   ├── execution.py          # Paper executor (simulated fills)
│   ├── backtest.py           # Candle-by-candle backtest engine
│   ├── metrics.py            # Sharpe, CAGR, max drawdown, win rate
│   ├── reporter.py           # JSON equity history persistence
│   ├── regime.py             # Market regime detector + strategy selector
│   ├── synth.py              # Deterministic synthetic price series
│   ├── dashboard.py          # Legacy stdlib HTTP server (replaced by FastAPI)
│   ├── strategy_api.py       # FastAPI unified server (API + SPA + equity)
│   ├── agent_analyzer.py     # Backtest risk classifier (ok/warn/alert)
│   └── reflection.py         # Post-backtest trade pattern analysis
├── dashboard/                # React frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── main.tsx          # React entrypoint
│   │   ├── Dashboard.tsx      # Main dashboard (equity chart, stats)
│   │   ├── EquityChart.tsx   # SVG area chart (pure, no chart libs)
│   │   ├── StatCard.tsx       # Metric card component
│   │   ├── types.ts           # Shared TypeScript types
│   │   ├── index.css          # Dark terminal-inspired theme
│   │   │
│   │   └── browse/           # Strategy browser & backtest UI
│   │       ├── api.ts            # API client (fetch-based)
│   │       ├── BrowseStrategies.tsx  # Strategy grid + filters
│   │       ├── BacktestReport.tsx    # Backtest detail view
│   │       ├── BacktestRunner.tsx    # Run backtest form
│   │       ├── AnalyzePage.tsx       # Agent analysis view
│   │       ├── StrategyCard.tsx      # Strategy card with sparkline
│   │       ├── FiltersBar.tsx        # KPI filter bar
│   │       ├── Sparkline.tsx         # Mini SVG sparkline
│   │       └── types.ts             # Strategy, BacktestReport types
│   │
│   ├── index.html            # SPA shell
│   ├── vite.config.ts        # Vite config + /api proxy
│   ├── vitest.config.ts      # Frontend test config
│   ├── tsconfig.json         # TypeScript config
│   ├── package.json          # Node dependencies
│   └── dist/                 # Production build (served by FastAPI)
├── tests/                    # Python test suite (111 tests)
│   ├── test_grid.py
│   ├── test_backtest.py
│   ├── test_backtest_risk.py
│   ├── test_continuous.py
│   ├── test_dashboard.py
│   ├── test_dynamic_grid.py
│   ├── test_execution.py
│   ├── test_indicators_extra.py
│   ├── test_metrics.py
│   ├── test_reflection.py
│   ├── test_regime.py
│   ├── test_reporter.py
│   ├── test_risk.py
│   ├── test_safety.py
│   ├── test_strategy_combined.py
│   ├── test_structure.py
│   ├── test_synth.py
│   ├── test_wallet.py
│   └── test_agent_analyzer.py
└── data/                     # Runtime data (gitignored)
    └── equity.json           # Equity history (created at runtime)
```

## Running Tests

```bash
# Python tests (111 tests, stdlib pytest)
python3 -m pytest tests/ -v

# Frontend tests (7 tests, vitest + jsdom)
cd dashboard && npm test

# Run both
python3 -m pytest tests/ -v && cd dashboard && npm test
```

## Code Quality

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
pyright .

# Dead code detection
vulture --min-confidence 65 .

# Dependency vulnerability check
safety check --full-report
```

The project uses [pre-commit](https://pre-commit.com/) with hooks for Ruff (lint + format), Pyright (type check), Vulture (dead code), and Safety (dependency vulnerabilities). Install with:

```bash
pip install pre-commit ruff pyright vulture safety
pre-commit install
```

## Specifications

Design constraints and guarantees that shape crypto-bot:

| Constraint | Guarantee |
|------------|-----------|
| **Paper-only** | No code path places a real order; live mode is blocked by default |
| **Stdlib-first** | Core domain logic (indicators, backtest, wallet, risk) imports zero third-party packages |
| **Zero look-ahead** | Backtest decisions at step `t` use only `closes[0..t]` |
| **Deterministic** | Same parameters → same result (no RNG in the core loop) |
| **No secrets** | Only public Binance endpoints are used; no API keys, no `.env` required |
| **Resilient loop** | Network/JSON failures are logged and skipped — the cycle never crashes |
| **Observable** | Every cycle persists equity to `data/equity.json` for live dashboard rendering |

## License

[MIT](LICENSE) — free for learning, experimentation, and extension. Not financial advice.
