---
id: SPEC-agent-trade-simulation
companions: []
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate.

# Agent Trade Simulation — bridging decision to execution

## Why

Agent Desk roda 5 agentes que decidem buy/sell/hold mas **nunca executam ordens**. `cli.py` ignora o agent desk e usa outro caminho (`_signal_for()`). Dois pipelines paralelos, nenhum converge — agente decide, ninguém escuta. Necessário unificar: agent desk decide → PaperEngine executa.

## Capabilities

- **CAP-1: Agent Desk executa ordens automaticamente**
  - **intent:** `agent_desk.run_cycle()` / `run_team()` submete ordem ao PaperEngine quando decisão for buy/sell com confiança >= 0.5, em REAL mode.
  - **success:** Ciclo agent desk faz buy BTCUSDT @ preço live, posição aparece no snapshot, audit trail registra cycle_id + order_id + fill price.

- **CAP-2: POST /api/agents/execute**
  - **intent:** Frontend pode disparar execução manual da última decisão do Agent Desk via endpoint REST.
  - **success:** `POST /api/agents/execute {cycle_id}` → 200 + ordem filled via PaperEngine. Mesmo cycle_id rejeitado (idempotente). DEMO mode retorna 403.

- **CAP-3: cli.py run_cycle() usa Agent Desk**
  - **intent:** `cli.py run_cycle()` substitui `_signal_for()` por `agent_desk.run_cycle()` e executa via `PaperEngine.submit()`.
  - **success:** `python cli.py --cycles 1` faz buy/sell/hold consistente com agents, sem caminho paralelo de estratégia.

- **CAP-4: Frontend AgentDesk.tsx botão "Executar"**
  - **intent:** Painel Agent Desk mostra decisão + botão "Executar" → POST /api/agents/execute → ordem executada. Botão oculto em DEMO.
  - **success:** 1 clique no agent verdict → ordem filled aparece no Trade Desk.

- **CAP-5: Histórico de execuções agentes**
  - **intent:** GET /api/agents/history retorna lista {cycle_id, decision, order_id, fill_price, status, timestamp}.
  - **success:** Cada execução agent → PaperEngine → registrada, visível no frontend.

## Constraints

- DEMO mode: agent desk decide mas NUNCA executa. CAP-4 oculto, /api/agents/execute retorna 403.
- qty calculada: `snapshot().available_cash * decision.confidence / last_price`, respeitando LOT_SIZE minQty. Máximo 1 posição por symbol.
- Idempotência: cycle_id único, mesmo cycle_id rejeitado se já executado.
- REAL mode exige `ALLOW_LIVE_TRADING=1`. Respeita `_MAX_DAILY_ORDERS` + `_MAX_EXPOSURE_PCT`.
- Presets sem DecisionCore (quant_desk, hedge_desk) não executam ordens — só análise.
- Apenas `crypto_trading_desk`, `investment_committee`, `scalping_desk` executam (têm DecisionCore + StrategyAgent).

## Non-goals

- Não substituir PaperEngine — agent desk usa `PaperEngine.submit()` existente.
- Não adicionar LLM no AgentDesk — adiado.
- Sem ML on-chain — agent desk é heurístico.
- Sem multi-symbol simultâneo no mesmo cycle — 1 cycle = 1 ordem no máximo.

## Success signal

1. `cli.py --cycles 3` faz 3 ordens paper consistentes com os agents. `cli.py` com `--strategy agent_desk`.
2. 1 clique no AgentDesk frontend → filled no TradeDesk + audit trail.
3. Todos 6 swarm presets rodam sem crash; 3 que executam produzem ordem.
4. `pytest tests/unit/test_agent_desk.py` + novos testes de integração passam.
