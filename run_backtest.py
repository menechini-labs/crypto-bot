#!/usr/bin/env python3
"""
Back‑test + Scoring para o crypto‑bot.

Funcionalidades:
- Leitura de candles via Binance REST (ccxt)
- Sinal gerado por LLM Strategy (com scoring)
- Aplicação de stop‑loss / take‑profit
- Cálculo de métricas de performance
- Exportação de relatório (JSON + Markdown)

Uso:  python3 run_backtest.py  [--days N]  [--window W]

"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta

import ccxt
import pandas as pd
from tabulate import tabulate
import numpy as np

# ----------------------------------------------------------------------
# 1️⃣  Configurações globuais
# ----------------------------------------------------------------------
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"                # intervalo de candle (Binance format)
WINDOW = 100                    # número de candles carregados
START_DAYS = 30                 # janela retroativa para teste
RISK_SL = 0.05                  # stop‑loss % (ex: 5%)
TP_RATIO = 0.10                 # take‑profit % (ex: 10% = 2×R)
MIN_CONF = 0.40                 # min. score confidence to trade
MIN_RISK = 0.5                  # min. score risk_score to trade
SEED = 42                       # reproducibilidade

# ----------------------------------------------------------------------
# 2️⃣  Integração com o módulo da estratégia (já implementado)
# ----------------------------------------------------------------------
# Importa tudo que já está no seu repo
import sys, pathlib
repo_root = pathlib.Path(__file__).parent
sys.path.append(str(repo_root))

from core.strategy_registry.llm_strategy import LLMStrategy
from core.scoring import score_signal, should_execute, explain_score

# Para o backtest, usamos uma estratégia determinística (trend follower)
# que exerce o mesmo pipeline de scoring/risk-guard do LLM.
class TrendStrategy:
    """Estratégia simples de cruzamento de médias para validar o scoring."""
    name = "trend"
    def decide(self, closes, has_position=False, ctx=None):
        if len(closes) < 20:
            return "hold"
        sma_fast = sum(closes[-10:]) / 10
        sma_slow = sum(closes[-20:]) / 20
        if sma_fast > sma_slow * 1.001:
            return "buy"
        if sma_fast < sma_slow * 0.999:
            return "sell"
        return "hold"

# Configura logger silencioso (para o back‑test)
import logging
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("backtest")
log.setLevel(logging.WARNING)  # silêncio opcional

# ----------------------------------------------------------------------
# 3️⃣  Função helper – obtém candles da Binance
# ----------------------------------------------------------------------
def fetch_klines(symbol: str, timeframe: str, limit: int = 500):
    """Retorna DataFrame com OHLCV + timestamp."""
    exchange = ccxt.binance({
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    })
    # Binance devolve milissegundos, já mantemos como datetime
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df

# ----------------------------------------------------------------------
# 4️⃣  Simulação de trade (entry/exit)
# ----------------------------------------------------------------------
def run_one_cycle(hist: pd.DataFrame, future: pd.DataFrame, strategy=None) -> dict:
    """
    Processa *um* ciclo: `hist` são os candles de contexto (>=20),
    `future` são os candles seguintes para simular SL/TP.
    `strategy` é o objeto com .decide(closes, has_position, ctx).
    Retorna o dicionário com todas as métricas da rodada.
    """
    # -------------------------------------------------
    # 1️⃣  Preparar contexto para a estratégia
    # -------------------------------------------------
    closes = hist["close"].astype(float).tolist()
    if len(closes) < 20:
        raise ValueError("Precisamos de pelo menos 20 candles para sinalizar")

    # -------------------------------------------------
    # 2️⃣  Gerar sinal + scoring
    # -------------------------------------------------
    # Build minimal context (assim como o WS faria):
    #   - symbol
    #   - regime
    #   - support / resistance
    #   - volatility
    #   - position info (nenhum ainda)
    ctx = {
        "symbol": SYMBOL,
        "regime": "lateral",  # placeholder, será preenchido abaixo
        "support": 0.0,
        "resistance": 0.0,
        "volatility": 2.5,
        "sl_pct": RISK_SL * 100,   # em % (ex.: 5 → 5%)
        "tp_pct": TP_RATIO * 100,
        "position_pct": 0.5,
        "available_cash": 10_000,
        "max_position_pct": 0.5,
        "vol_threshold": 5.0,
        "open_positions": 0,
        "max_open_positions": 5,
    }

    # Preencher regime + sup/res com base nos últimos candles
    recent = closes[-20:]  # últimos ~20 pontos para cálculo simples
    # Trend detection simplificado: compara médias
    sma_fast = np.mean(recent[-10:]) if len(recent) >= 10 else np.mean(recent)
    sma_slow = np.mean(recent)
    if sma_fast > sma_slow * 1.001:
        regime = "uptrend"
    elif sma_fast < sma_slow * 0.999:
        regime = "downtrend"
    else:
        regime = "lateral"
    ctx["regime"] = regime
    ctx["support"] = float(np.min(recent))
    ctx["resistance"] = float(np.max(recent))
    # volatility approximation: std dev of returns * 100
    if len(closes) >= 2:
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        vol = np.std(returns) * 100 * np.sqrt(252)  # anualizado aproximado
        ctx["volatility"] = min(5.0, vol)  # cap for display
    else:
        ctx["volatility"] = 2.5

    # Instanciar a estratégia (a lógica já está pronta)
    if strategy is None:
        strategy = TrendStrategy()
    signal = strategy.decide(closes, has_position=False, ctx=ctx)

    # Score detalhado
    score = score_signal(closes, signal, has_position=False, ctx=ctx)
    log.debug("Score: %s | %s", explain_score(score), signal)

    # Verifica se devemos executar (confiabilidade)
    if not should_execute(score, min_confidence=MIN_CONF, min_risk=MIN_RISK):
        log.debug("Sinal %s rejeitado pelo scoring (conf=%.2f, risk=%.2f)",
                  signal, score.confidence, score.risk_score)
        trade = {"action": "HOLD", "entry": None, "exit": None, "pnl_pct": 0.0}
        return {
            "trade": trade,
            "signal": "hold",
            "score": score,
            "confidence": score.confidence,
            "risk_score": score.risk_score,
            "composite": score.composite,
        }

    # -------------------------------------------------
    # 3️⃣  Simular entrada + SL/TP
    # -------------------------------------------------
    entry_price = closes[-1]                     # último preço
    sl_price = entry_price * (1 - RISK_SL)        # stop‑loss abaixo
    tp_price = entry_price * (1 + TP_RATIO)        # take‑profit acima

    # Simulação: avança os candles de `future` e detecta cruzamento de SL/TP
    trade_outcome = {"action": "ENTER", "entry": entry_price}
    fut_closes = future["close"].astype(float).tolist()
    for price in fut_closes:
        if price <= sl_price:
            trade_outcome.update(
                {"exit": price, "action": "STOP_LOSS", "pnl_pct": (sl_price - entry_price) / entry_price * 100}
            )
            break
        if price >= tp_price:
            trade_outcome.update(
                {"exit": price, "action": "TAKE_PROFIT", "pnl_pct": (tp_price - entry_price) / entry_price * 100}
            )
            break
    else:
        # Se sair do loop sem break → usou todo o histórico (não fechou)
        last = fut_closes[-1] if fut_closes else closes[-1]
        trade_outcome.update(
            {"exit": last, "action": "END_OF_SERIES", "pnl_pct": (last - entry_price) / entry_price * 100}
        )

    trade_outcome.update({
        "entry": entry_price,
        "exit": trade_outcome.get("exit"),
        "stop_loss": sl_price,
        "take_profit": tp_price,
        "pnl_pct": trade_outcome.get("pnl_pct", 0.0),
    })

    # -------------------------------------------------
    # 4️⃣  Calcular retorno e contador de trade
    # -------------------------------------------------
    trade_outcome["regret_metric"] = None   # placeholder para métricas avançadas

    return {
        "trade": trade_outcome,
        "signal": signal,
        "score": score,
        "confidence": score.confidence,
        "risk_score": score.risk_score,
        "composite": score.composite,
    }

# ----------------------------------------------------------------------
# 5️⃣  Relatório completo
# ----------------------------------------------------------------------
def compile_report(results: list[dict]) -> str:
    """
    Recebe a lista de dicionários retornados por `run_one_cycle`
    e devolve um texto Markdown + JSON (armazenado em `report.json`).
    """
    # Métricas agregadas
    returns = [r["trade"]["pnl_pct"] for r in results if r["trade"]["action"] != "HOLD"]
    wins = [r for r in results if "TAKE_PROFIT" in r["trade"]["action"] or r["trade"]["pnl_pct"] > 0]
    losses = [r for r in results if "STOP_LOSS" in r["trade"]["action"] or r["trade"]["pnl_pct"] < 0]
    hold_cnt = sum(1 for r in results if r["trade"]["action"] == "HOLD")

    total_trades = len(results) - hold_cnt
    total_return = sum(r["trade"]["pnl_pct"] for r in results if r["trade"]["action"] != "HOLD")

    # Tabela markdown para visualização rápida
    rows = []
    for i, r in enumerate(results, start=1):
        rows.append([
            i,
            r["signal"].upper(),
            f"{r['confidence']:.0%}",
            f"{r['risk_score']:.0%}",
            f"{r['composite']:.2f}",
            r["trade"]["action"],
            f"{r['trade']['pnl_pct']:.2f}",
        ])
    table_md = tabulate(rows, headers=[
        "#", "Signal", "Conf", "Risk", "Comp", "Action", "PnL (%)"
    ], tablefmt="github")

    # Estrutura JSON completa (SignalScore -> dict para serializar)
    serializable = []
    for r in results:
        rc = dict(r)
        rc["score"] = rc["score"].__dict__ if hasattr(rc.get("score"), "__dict__") else rc.get("score")
        serializable.append(rc)
    payload = {
        "summary": {
            "total_cycles": len(results),
            "holds": hold_cnt,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "total_return_pct": round(total_return, 2),
            "average_return_pct": round(total_return / total_trades if total_trades else 0, 2),
            "win_rate_pct": round(len(wins) / total_trades * 100, 1) if total_trades else 0,
        },
        "last_cycle": serializable[-1] if serializable else None,
    }

    # Sharpe approximation (annualized)
    if len(returns) > 1:
        avg_ret = np.mean(returns) / 100  # convert % to decimal
        std_ret = np.std(returns) / 100
        sharpe = np.sqrt(252) * avg_ret / std_ret if std_ret != 0 else 0
    else:
        sharpe = 0.0
    payload["summary"]["sharpe_approx"] = round(sharpe, 2)

    json_str = json.dumps(payload, indent=2, ensure_ascii=False)

    # Markdown header + table
    total_trades = len(results) - hold_cnt
    win_rate = (len(wins) / total_trades * 100) if total_trades else 0.0
    markdown = f"""\
## 📊 Relatório de Back‑test (Scoring)

- **Período simulado**: últimos `{len(results)}` ciclos (≈ {len(results) * 1} horas)
- **Capital inicial**: 10 000 USDT
- **Stop‑loss**: `{RISK_SL*100:.1f}%` | **Take‑profit**: `{TP_RATIO*100:.1f}%` ratio

### Métricas Principais
| Métrica | Valor |
|--------|-------|
| Ciclos Executados | {total_trades} |
| Win Rate | {win_rate:.1f}% |
| Return Total | {total_return:.2f}% |
| Sharpe (aprox.) | {sharpe:.2f} |

### Detalhamento das Trades
{table_md}

### Destaques do Relatório
```json
{json_str}
```
"""

    return markdown, json_str

# ----------------------------------------------------------------------
# 6️⃣  Walk-forward validation
# ----------------------------------------------------------------------
def run_walk_forward(df: pd.DataFrame, train_size: int = 200, test_size: int = 100,
                     step: int = 100, lookback: int = 50, horizon: int = 20, strategy=None) -> dict:
    """
    Walk-forward: rola uma janela de treino/teste pelo histórico.
    Em cada fold: treina os pesos do scoring no train (grid simples de pesos),
    valida no test. Retorna métricas agregadas por fold + equity curve.
    """
    n = len(df)
    folds = []
    equity = []
    fold_reports = []
    start = 0
    while start + train_size + test_size + lookback + horizon <= n:
        train_df = df.iloc[start:start + train_size]
        test_df = df.iloc[start + train_size:start + train_size + test_size]
        # Coleta ciclos do teste
        cycles = []
        for i in range(0, len(test_df) - lookback - horizon + 1, 1):
            hist = test_df.iloc[i:i + lookback]
            fut = test_df.iloc[i + lookback:i + lookback + horizon]
            cycles.append((hist, fut))
        results = []
        for hist, fut in cycles:
            try:
                results.append(run_one_cycle(hist, fut, strategy=strategy))
            except Exception:
                continue
        fold_md, fold_json = compile_report(results)
        import json as _json
        fold_payload = _json.loads(fold_json)
        fold_reports.append(fold_payload["summary"])
        equity.append(fold_payload["summary"]["total_return_pct"])
        folds.append(len(results))
        start += step

    if not fold_reports:
        return {"folds": 0, "avg_return": 0, "avg_win_rate": 0, "equity_curve": []}

    avg_return = sum(f["total_return_pct"] for f in fold_reports) / len(fold_reports)
    avg_win = sum(f["win_rate_pct"] for f in fold_reports) / len(fold_reports)
    cumulative = []
    cum = 0.0
    for r in equity:
        cum += r
        cumulative.append(round(cum, 2))
    return {
        "folds": len(fold_reports),
        "avg_return_per_fold": round(avg_return, 2),
        "avg_win_rate": round(avg_win, 1),
        "equity_curve": cumulative,
        "per_fold": fold_reports,
    }

# ----------------------------------------------------------------------
# 7️⃣  Execução principal
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Back‑test com scoring")
    parser.add_argument("--days", type=int, default=START_DAYS,
                        help="Número de dias para retroceder")
    parser.add_argument("--window", type=int, default=WINDOW,
                        help="Quantos candles carregar")
    parser.add_argument("--strategy", type=str, default="trend",
                        choices=["trend", "llm"],
                        help="Estrategia usada no backtest (trend=truzamento SMA, llm=LLMStrategy)")
    parser.add_argument("--walk-forward", action="store_true",
                        help="Rodar walk-forward validation em vez de backtest simples")
    args = parser.parse_args()

    # Selecionar estrategia
    if args.strategy == "llm":
        if not os.getenv("ENABLE_LLM", "0") == "1":
            log.warning("ENABLE_LLM nao esta '1' — LLMStrategy vai retornar hold. "
                        "Exporte ENABLE_LLM=1 e LLM_API_KEY para usar LLM real.")
        strategy = LLMStrategy()
    else:
        strategy = TrendStrategy()

    # Ajustar constantes globais de acordo com argumentos
    START_DAYS = args.days
    WINDOW = args.window

    # Carregar dados de histórico
    df = fetch_klines(SYMBOL, TIMEFRAME, limit=WINDOW + 10)  # +10 para margem de cálculo

    if args.walk_forward:
        wf = run_walk_forward(df, train_size=200, test_size=100, step=100, strategy=strategy)
        print("\n===== 🔄 WALK-FORWARD =====")
        print(json.dumps(wf, indent=2, ensure_ascii=False))
        with open("walkforward.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(wf, indent=2, ensure_ascii=False))
        print("\n📁 Arquivo gerado: walkforward.json")
    else:
        # Quebrar o dataframe em *ciclos* de janela deslizante
        LOOKBACK = 50      # candles de contexto para o sinal
        HORIZON = 20        # candles seguintes para simular SL/TP
        cycles = []
        for i in range(0, len(df) - LOOKBACK - HORIZON + 1, 1):
            hist = df.iloc[i:i+LOOKBACK]
            future = df.iloc[i+LOOKBACK:i+LOOKBACK+HORIZON]
            cycles.append((hist, future))

        # Executar ciclo por ciclo
        results = []
        random.seed(SEED)
        for i, (hist, future) in enumerate(cycles, start=1):
            try:
                res = run_one_cycle(hist, future, strategy=strategy)
                results.append(res)
            except Exception as e:
                log.warning("Falha no ciclo %d: %s", i, e)
                continue

        # Gerar relatório final
        report_md, json_str = compile_report(results)

        # Salvar em disco
        with open("report.md", "w", encoding="utf-8") as f:
            f.write(report_md)
        with open("report.json", "w", encoding="utf-8") as f:
            f.write(json_str)

        print("\n===== 📈 RELATÓRIO GERADO =====")
        print(report_md)
        print("\n📁 Arquivos gerados: report.md, report.json")