# crypto-bot (paper trading, spot)

Bot de trading de criptomoedas **simulado (paper)**, modo **spot** (sem alavancagem),
usando dados de mercado públicos via HTTP (Binance API pública). Sem chave de exchange,
sem saque, sem live trading.

O objetivo é **aprender o sistema**: coleta de dados, indicadores, estratégia, carteira
fictícia, gestão de risco e métricas de performance — sem risco de grana real.

## Estrutura

```
crypto-bot/
├── cli.py               # entrypoint (roda da raiz do projeto)
├── core/                # modulos de dominio
│   ├── config_loader.py # parser de config.yaml (stdlib)
│   ├── market.py        # fetch OHLCV da Binance (publica, sem auth)
│   ├── indicators.py    # MA, RSI, MACD, Bollinger (stdlib)
│   ├── strategy.py      # estrategias: grid, grid_dynamic, combined, baseline
│   ├── wallet.py        # carteira paper (compra/venda ficticia)
│   ├── risk.py          # stop-loss, take-profit, tamanho de posicao
│   ├── execution.py     # executor paper (mock, sem ordem real)
│   ├── backtest.py      # engine de backtest (sem look-ahead)
│   ├── reporter.py      # registra equity/PnL em JSON
│   ├── dashboard.py     # servidor HTTP que serve frontend React + /equity
│   ├── metrics.py       # Sharpe, CAGR, max drawdown, win-rate
│   ├── regime.py        # detector de regime de mercado + seletor de estrategia
│   └── synth.py         # gerador de series sinteticas (lateral/alta/queda)
├── dashboard/           # frontend React (Vite + TypeScript)
│   ├── src/             # Dashboard.tsx, EquityChart (SVG), StatCard
│   ├── dist/            # build estatico (servido pelo cli --mode dashboard)
│   └── vitest.config.ts # testes com jsdom
├── tests/               # 15+ arquivos de teste Python
├── config.yaml          # configuracao do bot
└── README.md
```

## Como rodar

```bash
python3 cli.py --mode once          # um ciclo (dados reais da Binance)
python3 cli.py --mode continuous    # loop a cada N segundos
python3 cli.py --mode report        # ultimos 10 registros de equity
python3 cli.py --mode dashboard     # servidor HTTP com frontend React
```

Opcoes extras:
- `--strategy grid|grid_dynamic|combined|default` — override da config
- `--interval N` — segundos entre ciclos (modo continuo)

## Dashboard React

O `--mode dashboard` sobe um servidor local (localhost:8000) que:
- Serve o **build estatico do React** (`dashboard/dist/`)
- Expoe `/equity` com o historico de equity/PnL em JSON (API para o frontend)

O frontend React mostra:
- Cards: Equity, PnL, Max Drawdown, posicoes abertas
- Grafico de area SVG (equity ao longo dos ciclos)
- Tabela de posicoes atuais
- Atualizacao automatica a cada 5s

**Build do frontend** (se mexer no `dashboard/src/`):
```bash
cd dashboard
npm install
NODE_ENV=development npx vite build   # gera dist/
```

## Estrategias

| Estrategia | Regime ideal | Descricao |
|-----------|-------------|-----------|
| grid | lateral | Compra em niveis descendentes, vende nos ascendentes |
| grid_dynamic | uptrend (alta forte) | Grid que recentraliza no preco atual |
| combined | queda (downtrend) | MA + RSI + MACD + Bollinger |
| default | — | MA cross simples |

**Seletor automatico** (`core/regime.py`): baseado na inclinacao da regressao linear dos ultimos closes.

## Backtest

```bash
python3 -c "
from core.backtest import run_backtest
from core.config_loader import load_config
from core.synth import make_series
cfg = load_config()
closes = make_series('lateral', n=500, seed=42)
rep = run_backtest(closes, cfg, symbol='TEST', strategy_name='grid')
print(rep)
"
```

Metricas retornadas: `sharpe`, `cagr`, `max_drawdown_pct`, `win_rate`, `trades`, `pnl_pct`.

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

## Frontend Lint

```bash
cd dashboard
npm install --include=dev
npx eslint src/
npx prettier --write .
NODE_ENV=development npx vitest run   # testes React
```

## Push para o GitHub (via bundle)

O push nao pode ser feito deste ambiente (sem SSH e token exposto). Use o **bundle portatil**:

```bash
# Na sua maquina (com SSH ou token valido):
git clone /caminho/do/crypto-bot.bundle crypto-bot
cd crypto-bot
git remote set-url origin git@github.com:menechini-labs/crypto-bot.git
git push -u origin develop master
```

O bundle esta em `/home/node/.openclaw/workspace/crypto-bot.bundle` (31K, contem todo o historico).

## Principios de seguranca

- Paper only. Nenhuma ordem sai da maquina.
- Spot only. Sem futuros, sem alavancagem, sem liquidacao.
- Sem credenciais. Usa so dados de mercado publicos.
- Logica de grid respeita stop-loss (5% configuravel).
- Live trading fica fora de escopo ate decisao explicita do usuario, com chave so de trading.

## Pipeline (estilo do usuario)

search -> plan -> tasks -> tdd -> sdd -> coding -> tests -> linter
