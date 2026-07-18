# Phase 2 Plan — Agent Desk + News

Companion to `frontend-daytrader-architecture.md` + `frontend-phase0-plan.md` + `frontend-phase1-plan.md`.
Goal: transparent multi-agent decision loop (Metrics / News / Risk / Strategy / DecisionCore)
and an aggregated crypto-news feed with sentiment/impact. Paper-only; free no-auth sources.

**STATUS: DONE (2026-07-17)** — backend `core/agent_desk.py` + `core/news.py` + endpoints;
frontend `AgentDesk.tsx` + `NewsFeed.tsx` wireados em `Dashboard.tsx` (tabs Agents / News).

## Backend
- `core/agent_desk.py` (NEW):
  - `run_cycle(closes?)` → dict com `agents[]` (5 AgentVerdict) + `decision`.
  - Agents: MetricsAgent (regime/vol/rsi via `core.scoring`), NewsAgent (`core.news`),
    RiskAgent (risk-guard thresholds via `config_loader`, paper_only), StrategyAgent
    (rank registry por fit de regime), DecisionCore (fusão ponderada → buy/sell/hold + conf).
  - Stdlib-only, sem LLM. DecisionCore pronto p/ ser substituído por LLM depois.
- `core/news.py` (NEW):
  - `fetch_news()` / `news_summary()` — RSS free no-auth (CoinDesk + Cointelegraph).
  - Sentimento heurístico (léxico PT/EN), flag de impacto (BTC/ETH/SEC/FED/ETF…),
    extração de símbolos (BTC/ETH/SOL…). Tolerante a falha de feed individual (try/except).
- `core/strategy_api.py`:
  - `GET /api/agents/cycle` → `agent_desk.run_cycle(_cached_closes)`.
  - `GET /api/news?limit=&sources=` → `news.fetch_news` agregado + sentiment/impact.

## Frontend
- `AgentDesk.tsx` (NEW): grid de AgentCard (nome, role, verdict, confiança, reasoning, métricas)
  + painel de DECISÃO (buy/sell/hold + conf). Auto-refresh 30s + botão "Rodar ciclo".
- `NewsFeed.tsx` (NEW): sentiment tags (▲/▬/▼), bloco "Alto impacto", lista de headlines
  (fonte, sentimento, IMPACTO, símbolos, link, data).
- `Dashboard.tsx`: tabs `agents` + `news` adicionadas; import + render.
- `index.css`: +.agent-desk, .agent-card, .news-feed, .tag, .news-item.

## Validação
- `agent_desk.run_cycle` → decision hold/buy/sell + 5 agents.
- `news.news_summary` → count + sentiment (sandbox sem net externa → 0 itens, aceitável;
  feeds reais retornam 25-30/feed quando há rede).
- `npm run build` passa (tsc + vite).

## Notas / próximos
- Phase 3 (Trade Desk paper): `core/risk.py` ordered gate + idempotency + trailing stop;
  `/api/positions`, `/api/orders`, Trade Desk UI.
- LLM DecisionCore (substituir fusão heurística) — fase futura.
- `external_sources.py` (mcp-api.trader.dev) ainda não integrado; pode alimentar News/Backtest.
