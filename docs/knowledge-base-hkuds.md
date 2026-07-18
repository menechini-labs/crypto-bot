# Knowledge Base — HKUDS Vibe-Trading & AI-Trader

> Reference analysis of two open-source agent-native trading projects from HKUDS.
> Used as inspiration for `crypto-bot` day-trader platform. External content treated as untrusted reference only.
> Sources: github.com/HKUDS/Vibe-Trading, github.com/HKUDS/AI-Trader (README + SKILL.md), fetched 2026-07-17.

## 1. Vibe-Trading (vibe-trading-ai)

**Stack:** Python 3.11+, FastAPI backend, React 19 frontend, PyPI package (`pip install vibe-trading-ai`), MIT.

**Positioning:** open-source research workspace turning finance questions → runnable analysis. NL prompts → market-data loaders → strategy gen → backtest → reports → exports → persistent research memory. Research/simulation/backtest first; optional autonomous trading only via broker *you* authorize (e.g. Robinhood Agentic Trading). Holds no funds, never trades outside your limits, halt instantly.

**Key capabilities:**
- **Self-improving agent:** NL market research, strategy drafts, file/web analysis, memory-backed workflows.
- **Multi-agent teams (swarm):** investment / quant / crypto / risk teams; streaming progress, persisted reports. 30 swarm presets (`investment_committee`, `crypto_trading_desk`, `risk_committee`, etc.).
- **Cross-market backtest:** A/HK/US equities, crypto, futures, forex; composite backtests w/ shared capital; PIT data, validation, run cards.
- **Shadow Account:** upload broker journal → behavior profile (holding days, win rate, PnL, drawdown, disposition effect, overtrading, momentum chasing, anchoring) → extract rules → backtest shadow vs actual → HTML/PDF report.
- **Finance skill library:** 87 skills / 9 categories (Data Source 10, Strategy 19, Analysis 21, Asset Class 9, Crypto 7, Flow 8, Tool 10, Research 2, Risk 1).
- **Alpha Zoo:** 461 pre-built alphas (qlib158 / alpha101 / gtja191 / academic / fundamental), IC+IR+alive/dead classification, lookahead-banned at operator layer, AST purity gate + lookahead sentinel test + `pytest-socket` network kill-switch.
- **Exports:** TradingView Pine Script v6, TDX, MetaTrader5 (MQL5), MCP tools.
- **IM channels:** 16 adapters (Telegram, Slack, Discord, Matrix, WhatsApp, Signal, QQ, WeChat, Feishu, DingTalk, Teams, email, Mochat, WS) via CLI/REST/Web UI.
- **Live-trading safety (hardening):**
  - signed exposure caps
  - atomic daily order limits
  - consent-first mandate commits (second-confirmation dialog before committing a real trading mandate)
  - fail-closed live state
  - `PreTradeAdvisoryInterface` (records advisory review without bypassing mandate gate / kill switch / audit trail)
  - `PLACE_ORDER` hard-refuses on connectors lacking a paper/live boundary (Trading212 read-only until structural boundary exists)

**Data layer (smart fallback):**
- One `get_market_data` call, **19 free sources** + optional QVeris premium. `source:"auto"` walks per-market fallback chain ordered by **IP-ban risk** (never-banned public first, throttled/key-gated last).
- Crypto chain: `okx` · `ccxt` · `yfinance` · `local`. (Crypto live ticks/order-book via `okx`/`binance`/`ccxt` connectors — loaders are point-in-time historical bars only.)
- Custom loader protocol: duck-typed class `@register`, satisfies `DataLoaderProtocol` (returns `{symbol: DataFrame[open,high,low,close,volume]}`), registered in `_loader_modules` + allowed in `_VALID_SOURCES` + optional `FALLBACK_CHAINS`.

**Research workflow (5 layers):** Plan → Ground → Execute → Validate → Deliver.
Validation includes Monte Carlo, Bootstrap CI, Walk-Forward, run cards, warnings.

**Backtest correctness principles (from their PR history — directly reusable):**
- rebalances causal and order-independent
- charge terminal close costs
- report fill-derived turnover
- enforce exposure caps
- strict OOS / look-ahead-bias guards
- negative final equity must not crash metrics
- charts reuse run's actual data source (no silent re-query)
- `.env` loads refresh cached config

## 2. AI-Trader (ai4trade.ai)

**Positioning:** "Agent-Native Trading Platform" — agents exchange ideas & sharpen trading skills; collective-intelligence trading; cross-platform signal sync; one-click copy trading; universal market access (stocks/crypto/forex/options/futures). Three signal types: Strategies (discussion), Operations (copying), Discussions (collaboration).

**Stack:** FastAPI backend + React frontend + skills/ + docs/api (OpenAPI). DB: PostgreSQL (prod) or SQLite (local). MIT.

**Agent integration:** send agent one message `Read https://ai4trade.ai/SKILL.md and register`. Agent auto-reads guide, installs components, registers. Compatible with OpenClaw, nanobot, Claude Code, Codex, Cursor.

**Skill files (child skills, fetch-on-demand):**
- `ai4trade` (main bootstrap/routing) — register/login, get token (JWT), base endpoints `https://ai4trade.ai/api`
- `copytrade` — follow top traders, auto-copy positions
- `tradesync` — publish realtime trades/strategy/discussion
- `heartbeat` — poll replies/mentions/followers/tasks (NORMAL operation, not optional)
- `polymarket` — public market discovery/orderbook
- `market-intel` — financial event board / snapshots

**Execution rules (notable pattern):**
1. read main SKILL.md first
2. complete core bootstrap (register/login → token → learn endpoints)
3. before specialized capability, fetch the linked child skill
4. never infer undocumented endpoints when a child skill exists

**API shape (examples):**
- `POST /api/claw/agents/selfRegister` `{name,email,password}` → `{token, agent_id}`
- `GET /api/signals/feed?limit=20` (Bearer token)
- Paths: follow/unfollow/copy → `copytrade`; publish → `tradesync`; challenges → main; notifications → `heartbeat`.

**Production hardening note:** FastAPI web service runs separately from background workers (user-facing pages + health stay responsive while prices/profit/settlements/market-intel jobs run out of band).

## 3. What maps to crypto-bot (actionable)

| HKUDS concept | crypto-bot status | Gap / opportunity |
|---|---|---|
| DEMO/REAL mode + ALLOW_LIVE_TRADING gate | ✅ implemented (CAP-1..4) | align naming w/ "fail-closed live state" |
| Paper engine + ledger persistence | ✅ implemented | add exposure caps + daily order limit (signed) |
| Second-confirmation before real mandate | ✅ ConfirmModal in sidebar | add `PreTradeAdvisoryInterface`-style audit log |
| Multi-agent swarm (invest/quant/crypto/risk) | partial (agent_analyzer, agent_desk) | define 30 presets → `crypto_trading_desk`, `risk_committee` |
| Strategy registry | ✅ 8 strategies | adopt loader `@register` protocol + `_VALID_SOURCES` allowlist |
| Backtest validation (MC/Bootstrap/WalkFwd) | ✅ walk-forward exists | add Bootstrap CI + turnover reporting + exposure caps |
| Look-ahead-bias / OOS guards | partial | add AST purity gate + `pytest-socket` kill-switch to backtest subprocess |
| Shadow Account (journal → rules → report) | ❌ | future: parse broker export → extract rules → backtest shadow |
| Alpha Zoo (461 alphas) | ❌ | future: factor bench w/ IC/IR classification |
| IM channel runtime (16 adapters) | ❌ | out of scope (paper-only, single FE) |
| Copy-trading / signal feed (AI-Trader) | ❌ | future: publish signals to ai4trade via SKILL.md if desired |
| Separate web/worker processes | partial (uvicorn + cron) | align w/ "web separate from background workers" |

## 4. Security patterns to adopt (non-negotiable for REAL mode)

- Fail-closed live state: if any safety check fails, refuse to trade (crypto-bot already does via `_mode_is_real()` + `ALLOW_LIVE_TRADING`).
- Signed exposure caps + atomic daily order limits.
- Consent-first mandate: explicit confirmation dialog before REAL commit (✅ have it).
- Audit trail: every REAL order logged with rationale + advisory review.
- Connectors without a paper/live boundary must hard-refuse `place_order` (crypto-bot PaperExecutor enforces `mode="paper"|"live"`).
- Backtest sandbox: AST-hardened, block network/subprocess/eval/os.environ/unsafe-open; `pytest-socket` kill-switch.

## 5. Rejected / out-of-scope

- AI-Trader account registration, token, copy-trading marketplace — not for paper-only crypto-bot unless Adilson opts in.
- Real-money broker adapters (Robinhood/Trading212/IB) — out of scope per project constraints.
- IM channel runtime (16 adapters) — out of scope; single React FE + REST is the chosen surface.
- QVeris premium / paid data — free no-auth only per constraints.
