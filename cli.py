"""CLI do paper bot (spot, sem risco real).

Uso:
  python3 cli.py --mode once
  python3 cli.py --mode continuous --interval 60

Nunca envia ordem real. Apenas simula compra/venda numa carteira fictícia.
Estratégia primaria: grid (melhor em lateral, ver backtest).
"""
import argparse
import sys
import time

from config_loader import load_config
from market import fetch_ohlcv
from wallet import PaperWallet
from risk import RiskManager
from execution import PaperExecutor
from reporter import append_equity, load_history

STRATEGY_DEFAULT = "grid"
EQUITY_PATH = "data/equity.json"


def _signal_for(strategy: str, closes: list[float], grid_levels, has_position: bool) -> str:
    if strategy == "grid":
        from strategy import decide_grid
        return decide_grid(closes, grid_levels, has_position)
    if strategy == "combined":
        from strategy import decide_combined
        return decide_combined(closes)
    # baseline
    from strategy import decide
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
        if strategy == "grid":
            from strategy import build_grid
            lo, hi = min(closes), max(closes)
            lo, hi = lo * 1.02, hi * 0.98
            grid_levels = build_grid(lo, hi, n=10)

        signal = _signal_for(strategy, closes, grid_levels, has_position)
        entry = wallet.positions.get(symbol, {}).get("avg_price")

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
    # registra snapshot do ciclo para o dashboard local
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
    ap.add_argument("--mode", choices=["once", "continuous"], default="once")
    ap.add_argument("--interval", type=int, default=60, help="segundos entre ciclos")
    ap.add_argument("--strategy", choices=["grid", "combined", "default"], default=None,
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
