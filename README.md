# crypto-bot (paper trading, spot)

Bot de trading de criptomoedas **simulado (paper)**, modo **spot** (sem alavancagem),
usando dados de mercado públicos via `ccxt`. Sem chave de exchange, sem saque, sem live trading.

O objetivo é **aprender o sistema**: coleta de dados, indicadores, estratégia, carteira
fictícia e gestão de risco — sem risco de grana real.

Inspirado na arquitetura do LLM-TradeBot (multi-agente), mas construído do zero e mantido
isolado: o módulo de execução só simula; nunca envia ordem para uma exchange.

## Lint + Safety (pre-commit)
Recomendado rodar Ruff, Pyright, Vulture e Safety antes de cada commit.

```bash
pip install pre-commit ruff pyright vulture safety
pre-commit install
# ou rodar manual:
ruff check . && ruff format . && pyright . && vulture --min-confidence 65 . && safety check
```

Configs:
- `ruff.toml` — regras (E,F,I,B,A,C4,SIM,N,UP,S...)
- `.pre-commit-config.yaml` — hooks: ruff, ruff-format, pyright, vulture (min-confidence 65), safety.

> O container deste ambiente nao tem pip/venv, entao os hooks ficam
> configurados mas exigem provisionar o ambiente antes de executar.

Safety em código (independente do hook): `tests/test_safety.py` garante que
live trading so ocorre com `ALLOW_LIVE_TRADING=1` explicito, e paper nunca
faz chamada de rede pra exchange.

## Princípios de segurança
- Paper only. Nenhuma ordem sai da máquina.
- Spot only. Sem futuros, sem alavancagem, sem liquidação.
- Sem credenciais. Usa só market data público (free).
- Live trading fica fora de escopo até decisão explícita do usuário, com chave só de trading.

## Pipeline (estilo do usuário)
search -> plan -> tasks -> tdd -> sdd -> coding -> tests -> linter
