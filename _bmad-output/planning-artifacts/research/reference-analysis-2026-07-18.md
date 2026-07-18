# 📋 Análise de Referências & Recomendações — Crypto-Bot

**Autor:** John (PM)
**Data:** 2026-07-18
**Objetivo:** Extrair padrões de 3 projetos open-source e priorizar melhorias no crypto-bot.

---

## 🔗 Referências Analisadas

| Projeto | Stack | Diferencial |
|---------|-------|-------------|
| **Crypto-Risk-Labs-v0** | Python, FastAPI, React, SQLite | Monte Carlo + blended confidence + Telegram |
| **AI-Trader** (GoGoButters) | Python, Graphiti, Perplexica | Memória de longo prazo + LLM search |
| **LLM-News-Paper-Trader** | Python, SQLite, Codex | Event-driven + source reliability + guards |

---

## 🥇 Recomendações Prioritárias

### 1. Post-Classification Guard (no `agent_desk.py`)
**Inspiração:** LLM-News-Paper-Trader — Codex classifica, Python decide.

**Problema:** Hoje o LLMDecisionCore decide direto. Se o LLM dá score alto mas a notícia contradiz, executa.

**O que fazer:**
- Adicionar `PostClassificationGuard` entre LLMDecisionCore e execução
- Regras: se LLM diz `buy` mas sentimento geral das notícias é negativo → reduz confidence em 20%
- Se fonte da notícia é `cointelegraph` (menos confiável) → penaliza
- Se `event_type` mapeado como `market_noise` → força `hold`

**Impacto:** Evita trade em falso positivo. Baixo esforço (2-3 funções).

---

### 2. Source Reliability Metadata (no `news.py` + `agent_desk.py`)
**Inspiração:** LLM-News-Paper-Trader — pesos diferentes por fonte.

**Problema:** Hoje `news.py` trata CoinDesk e Cointelegraph com o mesmo peso.

**O que fazer:**
- Adicionar `reliability` field em `NewsItem` / feed config
- `coindesk: 0.8`, `cointelegraph: 0.6`, `twitter: 0.3` (futuro)
- `NewsAgent` usa reliability no score final: `confidence *= reliability`

**Impacto:** Qualidade de sinal melhora sem mudar arquitetura. 1h.

---

### 3. Template Risk Framework (no `paper_engine.py`)
**Inspiração:** CRL Bot — 5 padrões (Triangle, Channel, Wedge, Reversal, Box) com SL/TP pré-calibrados.

**Problema:** Hoje SL/TP são fixos (2%/5%) independente do setup.

**O que fazer:**
- Adicionar `RiskTemplate` dataclass: `pattern → sl_pct, tp_pct, trailing_pct`
- `paper_engine.py` usa template se `order.pattern` for fornecido
- `agent_desk.py` infere pattern do regime atual via `scoring.detect_regime`

**Impacto:** Consistência de risco. 2-3h.

---

### 4. Blended Confidence (no `scoring.py`)
**Inspiração:** CRL Bot — 5 fontes: Monte Carlo + historical win-rate + ML pattern + price level + template.

**Problema:** Hoje `score_signal` usa só trend + momentum + volatility + RR + regime.

**O que fazer:**
- Adicionar `HistoricalHitRate` (lê `reflections.json` → win-rate por regime)
- Adicionar `MonteCarloSim` simples (200 trajetórias com vol atual)
- Blended confidence = weighted average de: `scoring.composite` + `historical` + `monte_carlo`
- Pesos: 0.5 / 0.25 / 0.25

**Impacto:** Decisão mais robusta que qualquer fonte isolada. 4-5h.

---

### 5. Graphiti Memory (no `reflection.py`)
**Inspiração:** AI-Trader — Graphiti knowledge graph.

**Problema:** `reflection.py` salva em JSON, mas não consegue responder "quando foi a última vez que esse padrão aconteceu?".

**O que fazer:**
- Adicionar `KnowledgeGraph` cliente (Graphiti ou Neo4j leve)
- `ReflectionAgent` persiste trades como nós (asset, regime, outcome)
- `DecisionCore` consulta: "teve setup similar? qual foi o resultado?"

**Impacto:** Aprendizado contínuo entre ciclos. 6-8h (depende de infra).

---

### 6. Event-Driven Layer (separado do `market_ws.py`)
**Inspiração:** LLM-News-Paper-Trader — SEC EDGAR + earnings calendar + news → filtra antes do LLM.

**Problema:** Hoje `news.py` só puxa RSS. Sem eventos estruturados (earnings, filings).

**O que fazer:**
- Adicionar `EventCollector`: earnings calendar (Yahoo Finance), SEC filings (EDGAR RSS), macro data
- `EventCollector` alimenta `Event` dataclass: `type, ticker, timestamp, reliability`
- `agent_desk.NewsAgent` consome eventos + notícias

**Impacto:** Pipeline completo, reduz noise. 3-4h.

---

### 7. Overreaction Detection (no `paper_engine.py`)
**Inspiração:** LLM-News-Paper-Trader — "buy the dip" com regras.

**Problema:** Hoje não há detecção de overreaction. Se BTC cai 5% num dia, pode comprar sem contexto.

**O que fazer:**
- Adicionar `OverreactionDetector`:
  - Stock caiu >X% em 1 dia
  - Underperforming benchmark (BTC vs SPY no caso crypto)
  - Sem notícia bearish de alta confiança
  - Volume anormal
- Se overreaction detectada → permite entrada reduzida (50% do sizing normal)

**Impacto:** Evita comprar queda que ainda tem mais queda. 2-3h.

---

### 8. Telegram Bot (canal alternativo)
**Inspiração:** CRL Bot — `/analyze`, `/photo`, `/trades`.

**Problema:** Hoje só dashboard web. Sem acesso mobile rápido.

**O que fazer:**
- Bot Telegram mínimo: `/status` → snapshot, `/trade [ideia]` → analisa com agent desk
- Reusa `agent_desk.run_cycle` + `paper_engine.snapshot`

**Impacto:** UX alternativa, acesso rápido. 4-5h (MVP).

---

## 📊 Matriz de Priorização

| # | Melhoria | Esforço | Impacto | Dependências |
|---|----------|---------|---------|--------------|
| 1 | Post-Classification Guard | ⭐ Baixo | 🔥 Alto | Nenhuma |
| 2 | Source Reliability | ⭐ Baixo | 🔥 Alto | Nenhuma |
| 3 | Template Risk Framework | ⭐⭐ Médio | 🔥🔥 Muito Alto | `paper_engine` |
| 4 | Blended Confidence | ⭐⭐⭐ Alto | 🔥🔥 Muito Alto | `scoring`, `reflection` |
| 5 | Graphiti Memory | ⭐⭐⭐⭐ Muito Alto | 🔥 Alto | Infra externa |
| 6 | Event-Driven Layer | ⭐⭐⭐ Médio | 🔥🔥 Alto | `news`, `agent_desk` |
| 7 | Overreaction Detection | ⭐⭐ Médio | 🔥 Médio | `paper_engine` |
| 8 | Telegram Bot | ⭐⭐⭐ Alto | 🔥 Médio | API + deploy |

---

## 🚀 Próximos Passos (Sprint Atual)

**Quick wins (1-2):** Post-Classification Guard + Source Reliability → implementar hoje.
**Sprint seguinte (3-4-7):** Template Risk + Blended Confidence + Overreaction.
**Backlog (5-6-8):** Graphiti, Event-Driven, Telegram.

Quer que eu detalhe a implementação de algum desses? Ou prefere começar pelos quick wins?

📋 _John, PM_
