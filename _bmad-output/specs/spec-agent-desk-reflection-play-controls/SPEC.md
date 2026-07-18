---
id: SPEC-agent-desk-reflection-play-controls
companions: []
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only.

# Agent Desk: Reflection por ciclo + controles PLAY (lock stop, meta, auto buy/sell)

## Why

Pain to solve. O usuário opera o Agent Desk pelo frontend e não consegue (1) usar Reflection dos agentes por ciclo — o backend só expõe reflection de backtest, sem endpoint nem UI no AgentDesk; e (2) controlar o PLAY: o loop automático hardcoded SL/TP/trailing e executa sempre que conf≥0.5, sem trava de saída (lock stop), sem meta (take-profit alvo), e sem poder desligar a execução automática. Quem é afetado: operador do dashboard (Adilson) em modo REAL. Importa agora porque PLAY sem controle de risco é inseguro e Reflection é a única forma de auditar decisões dos agentes.

## Capabilities

- **CAP-1** Reflection por ciclo de agente acessível no frontend
  - **intent:** Usuário pode disparar e visualizar reflection de um ciclo de agente específico (insights) e ver histórico de reflections, direto no AgentDesk.
  - **success:** `POST /api/agents/cycle/{cycle_id}/reflection` retorna insights e persiste; `GET /api/agents/reflections` lista; botão "Reflect" no AgentDesk abre painel com insights + histórico e responde 200.

- **CAP-2** PLAY com controles configuráveis antes de iniciar
  - **intent:** Usuário define SL%, TP%, Trailing%, Meta, Auto (on/off) e Lock Stop (on/off) num form no AgentDesk antes de apertar PLAY; o loop respeita esses valores.
  - **success:** `POST /api/agents/loop/start` aceita `sl_pct, tp_pct, trailing_pct, target_price, auto_trade, lock_stop` e o worker aplica; UI tem os 6 campos e os envia no PLAY.

- **CAP-3** PLAY em modo "só análise" quando auto desligado
  - **intent:** Com `auto_trade=false`, o PLAY roda ciclos e decide, mas nunca executa ordem — usuário executa manual pelo botão "Executar ordem" existente.
  - **success:** Com `auto_trade=false` o worker pula `engine.submit`; nenhuma posição aberta por ele; log mostra "análise only".

- **CAP-4** Lock Stop trava saída por stop-loss abaixo de piso
  - **intent:** Com `lock_stop=true`, o loop não fecha a posição por stop-loss enquanto o preço estiver acima do piso definido; saída por meta/TP continua permitida.
  - **success:** Com `lock_stop=true` e preço acima do piso, `engine.submit` de saída por SL é suprimido; saída por `target_price` ainda ocorre. (Semântica exata em open_questions OQ-1.)

- **CAP-5** Meta (target_price) define take-profit em preço absoluto
  - **intent:** Usuário informa preço-alvo absoluto; o loop fecha a posição ao atingir esse preço.
  - **success:** `target_price` não-nulo faz o worker enviar ordem de saída ao preço ≥ `target_price`; teste unit confirma gatilho. (Formato $ vs % em OQ-2.)

## Constraints

- Reflection de agente hoje existe só para backtests (`/api/backtest/{id}/reflection`, `/api/reflections`); AgentDesk não tem reflection por ciclo nem UI — novo endpoint + UI são obrigatórios, não patch de existente.
- `_agent_loop_worker` hardcode `sl_pct=0.02, tp_pct=0.05, trailing_pct=0.01` e executa automático sempre que `verdict in (buy,sell) and conf>=0.5` — controles devem substituir esses literais por parâmetros do PLAY.
- PLAY/loop só funciona em modo REAL (`_MODE=="real"` e `ALLOW_LIVE_TRADING=1`); demo continua só-análise. Controles de PLAY não relaxam essa guarda.
- Build do frontend (Vite) e testes (vitest) devem continuar verdes; servidor unificado (API + SPA em `dashboard/dist/`) deve subir e responder 200 em todas as rotas.

## Non-goals

- Não alterar reflection de backtest existente (`/api/backtest/{id}/reflection`) — apenas adicionar o caminho por ciclo de agente.
- Não mudar a guarda de modo REAL do PLAY (segurança).
- Não implementar estratégia de saída nova além de SL/TP/trailing + lock stop + meta (sem trailing-complex, sem parcial).
- Não persiste config de PLAY entre reinícios do servidor (escopo desta spec).

## Success signal

Operador abre Agent Desk, aperta "Reflect" num ciclo e vê insights + histórico; configura SL/TP/Trailing/Meta/Auto/Lock Stop, aperta PLAY em REAL, e o loop executa (ou só analisa, se Auto off) respeitando lock stop e meta — sem erro de JSON e com todas as rotas do servidor em 200.

## Open Questions

- **OQ-1** Lock stop: "não dispara SL abaixo de piso X" (trava saída só pra baixo, mas sai por meta) OU "trava posição inteira até TP/meta" (não sai de jeito nenhum)? Suspeita do autor: não sai por SL abaixo de X, mas sai por meta.
- **OQ-2** Meta (`target_price`): preço absoluto (ex: $64.000) OU % de lucro (ex: +10%) OU ambos? Spec usa preço absoluto por padrão; confirmar se % também.
- **OQ-3** `auto_trade=false` = PLAY vira "só analisa e avisa" e usuário executa manual pelo botão "Executar ordem" existente? Confirmar que esse é o comportamento desejado.
