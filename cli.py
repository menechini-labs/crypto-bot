"""CLI do paper bot (spot, sem risco real).

Uso:
  python3 cli.py --mode once
  python3 cli.py --mode continuous --interval 60

Nunca envia ordem real. Apenas simula compra/venda numa carteira fictícia.
Estratégia primaria: grid (melhor em lateral, ver backtest).
"""
import argparse
import os
import sys
import time

# permite rodar 'python3 cli.py' a partir da raiz do projeto
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.config_loader import load_config
from core.execution import PaperExecutor
from core.market import fetch_ohlcv
from core.reporter import append_equity, load_history
from core.risk import RiskManager
from core.wallet import PaperWallet

STRATEGY_DEFAULT = "grid"
EQUITY_PATH = os.path.join(ROOT, "data", "equity.json")


def _signal_for(strategy: str, closes: list[float], grid_levels, has_position: bool) -> str:
    if strategy == "grid":
        from core.strategy import decide_grid
        return decide_grid(closes, grid_levels, has_position)
    if strategy == "grid_dynamic":
        from core.strategy import decide_dynamic_grid
        return decide_dynamic_grid(closes, grid_levels, has_position)
    if strategy == "combined":
        from core.strategy import decide_combined
        return decide_combined(closes)
    from core.strategy import decide
    return decide(closes)


def run_cycle(cfg: dict, wallet: PaperWallet | None = None) -> PaperWallet:
    """Executa um ciclo de decisao para todos os simbolos.

    Em caso de falha de rede (market data), apenas loga e segue.
    Retorna o wallet atualizado (cria um novo se nao fornecido).
    """
    strategy = cfg.get("strategy", STRATEGY_DEFAULT)
    wallet = wallet or PaperWallet(
        initial_cash=cfg["initial_cash_usdt"], fee_pct=cfg["fee_pct"]
    )
    wallet.next_cycle()
    cycle = wallet._cycle
    risk = RiskManager(
        max_position_pct=cfg["max_position_pct"],
        stop_loss_pct=cfg["stop_loss_pct"],
        take_profit_pct=cfg["take_profit_pct"],
    )
    executor = PaperExecutor(mode="paper")
    current_prices: dict[str, float] = {}

    for symbol in cfg["symbols"]:
        try:
            candles = fetch_ohlcv(symbol, cfg["timeframe"], cfg["lookback"])
        except RuntimeError as e:
            print(f"[warn] {symbol}: falha ao buscar dados ({e}); pulando ciclo.")
            continue
        closes = [c["close"] for c in candles]
        last_price = closes[-1]
        current_prices[symbol] = last_price
        has_position = symbol in wallet.positions

        grid_levels = None
        if strategy in ("grid", "grid_dynamic"):
            from core.strategy import build_dynamic_grid, build_grid
            if strategy == "grid":
                lo, hi = min(closes), max(closes)
                lo, hi = lo * 1.02, hi * 0.98
                grid_levels = build_grid(lo, hi, n=10)
            else:
                center = closes[-1]
                step = max(last_price * 0.01, 1e-8)
                grid_levels = build_dynamic_grid(center=center, step=step, n=11)

        signal = _signal_for(strategy, closes, grid_levels, has_position)
        entry = wallet.positions.get(symbol, {}).get("avg_price")

        # Gate de scoring: mesmo criterio do backtest (confianca>=0.4, risco>=0.5)
        use_scoring = cfg.get("use_scoring", True)
        if use_scoring and signal == "buy" and not has_position:
            try:
                from core.scoring import score_signal, should_execute
                sctx = {
                    "symbol": symbol,
                    "regime": cfg.get("regime", "lateral"),
                    "volatility": cfg.get("volatility", 2.5),
                    "sl_pct": cfg["stop_loss_pct"] * 100,
                    "tp_pct": cfg["take_profit_pct"] * 100,
                }
                _score = score_signal(closes, "buy", has_position=False, ctx=sctx)
                if not should_execute(_score, min_confidence=0.4, min_risk=0.5):
                    print(f"{symbol}: BUY rejeitado pelo scoring (conf={_score.confidence:.2f} risk={_score.risk_score:.2f})")
                    signal = "hold"
            except Exception as e:
                print(f"[warn] {symbol}: scoring indisponivel ({e}); seguindo sem gate.")

        if has_position and entry:
            if risk.should_stop_loss(entry, last_price):
                executor.execute_sell(symbol, last_price)
                wallet.sell(symbol, last_price)
                print(f"{symbol}: STOP-LOSS @ {last_price:.2f}")
            elif risk.should_take_profit(entry, last_price):
                executor.execute_sell(symbol, last_price)
                wallet.sell(symbol, last_price)
                print(f"{symbol}: TAKE-PROFIT @ {last_price:.2f}")

        elif signal == "buy":
            notional = risk.max_notional(wallet.cash)
            if notional > 0:
                executor.execute_buy(symbol, last_price, notional)
                wallet.buy(symbol, last_price, notional)
                print(f"{symbol}: BUY ${notional:.2f} @ {last_price:.2f}")

        equity = wallet.equity({symbol: last_price})
        pnl = equity - cfg["initial_cash_usdt"]
        print(f"{symbol}: {last_price:.2f} | {signal} | equity ${equity:.2f} | PnL ${pnl:.2f}")

    total_equity = wallet.total_equity(prices=current_prices)
    append_equity(
        EQUITY_PATH,
        cycle=cycle,
        equity=total_equity,
        pnl=total_equity - cfg["initial_cash_usdt"],
        positions=wallet.positions,
    )
    return wallet


def main():
    ap = argparse.ArgumentParser(description="Paper trading bot (spot, sem risco real)")
    ap.add_argument("--mode", choices=["once", "continuous", "report", "dashboard"], default="once")
    ap.add_argument("--interval", type=int, default=60, help="segundos entre ciclos")
    ap.add_argument("--strategy", choices=["grid", "grid_dynamic", "combined", "default"], default=None,
                    help="estrategia (override do config)")
    args = ap.parse_args()

    try:
        cfg = load_config()
    except FileNotFoundError:
        print("config.yaml não encontrado.", file=sys.stderr)
        sys.exit(1)
    if args.strategy:
        cfg["strategy"] = args.strategy

    wallet = PaperWallet(initial_cash=cfg["initial_cash_usdt"], fee_pct=cfg["fee_pct"])
    print(f"=== Paper Bot (spot) | estrategia={cfg.get('strategy', STRATEGY_DEFAULT)} | caixa ${wallet.cash:.2f} ===")

    if args.mode == "once":
        run_cycle(cfg, wallet)
        print(f"=== Caixa ${wallet.cash:.2f} | Posicoes {list(wallet.positions)} ===")
    elif args.mode == "report":
        hist = load_history(EQUITY_PATH)
        if not hist:
            print("Sem histórico ainda. Rode --mode continuous.")
            return
        for rec in hist[-10:]:
            print(f"ciclo {rec['cycle']}: equity ${rec['equity']:.2f} | PnL ${rec['pnl']:.2f}")
    elif args.mode == "dashboard":
        try:
            import uvicorn
        except ImportError:
            print("Instale dependencias: pip install 'uvicorn[standard]'", file=sys.stderr)
            sys.exit(1)
        from core.strategy_api import app
        print("=== Servidor unificado (API + Frontend) em http://localhost:8000 ===")
        uvicorn.run(app, host="localhost", port=8000, log_level="info")
    else:
        print("Modo contínuo (Ctrl+C para parar). Paper only, sem risco real.")
        try:
            while True:
                wallet = run_cycle(cfg, wallet)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\nEncerrado. Caixa ${wallet.cash:.2f} | Posicoes {list(wallet.positions)}")


if __name__ == "__main__":
    main()
