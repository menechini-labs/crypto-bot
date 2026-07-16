"""CLI do paper bot (spot, sem risco real).

Uso:
  python3 cli.py --mode once
  python3 cli.py --mode continuous --interval 60

Nunca envia ordem real. Apenas simula compra/venda numa carteira fictícia.
"""
import argparse
import sys
import time

from config_loader import load_config
from market import fetch_ohlcv
from strategy import decide
from wallet import PaperWallet
from risk import RiskManager
from execution import PaperExecutor


def run_once(cfg: dict):
    wallet = PaperWallet(
        initial_cash=cfg["initial_cash_usdt"], fee_pct=cfg["fee_pct"]
    )
    risk = RiskManager(
        max_position_pct=cfg["max_position_pct"],
        stop_loss_pct=cfg["stop_loss_pct"],
        take_profit_pct=cfg["take_profit_pct"],
    )
    executor = PaperExecutor(mode="paper")

    print(f"=== Paper Bot (spot) | caixa inicial ${wallet.cash:.2f} ===")
    for symbol in cfg["symbols"]:
        candles = fetch_ohlcv(symbol, cfg["timeframe"], cfg["lookback"])
        closes = [c["close"] for c in candles]
        last_price = closes[-1]
        signal = decide(closes)

        current_prices = {symbol: last_price}
        entry = wallet.positions.get(symbol, {}).get("avg_price")

        # gestão de risco em posição aberta
        if symbol in wallet.positions and entry:
            if risk.should_stop_loss(entry, last_price):
                fill = executor.execute_sell(symbol, last_price)
                wallet.sell(symbol, last_price)
                print(f"{symbol}: STOP-LOSS -> venda simulada @ {last_price:.2f} {fill['status']}")
            elif risk.should_take_profit(entry, last_price):
                fill = executor.execute_sell(symbol, last_price)
                wallet.sell(symbol, last_price)
                print(f"{symbol}: TAKE-PROFIT -> venda simulada @ {last_price:.2f} {fill['status']}")

        # sinal de entrada
        elif signal == "buy":
            notional = risk.max_notional(wallet.cash)
            if notional > 0:
                fill = executor.execute_buy(symbol, last_price, notional)
                wallet.buy(symbol, last_price, notional)
                print(f"{symbol}: BUY simulado notional ${notional:.2f} @ {last_price:.2f} {fill['status']}")

        equity = wallet.equity(current_prices)
        pnl = equity - cfg["initial_cash_usdt"]
        print(f"{symbol}: preço {last_price:.2f} | sinal {signal} | equity ${equity:.2f} | PnL ${pnl:.2f}")
    print(f"=== Caixa final ${wallet.cash:.2f} | Posições {list(wallet.positions)} ===")


def main():
    ap = argparse.ArgumentParser(description="Paper trading bot (spot, sem risco real)")
    ap.add_argument("--mode", choices=["once", "continuous"], default="once")
    ap.add_argument("--interval", type=int, default=60, help="segundos entre ciclos")
    args = ap.parse_args()

    try:
        cfg = load_config()
    except FileNotFoundError:
        print("config.yaml não encontrado.", file=sys.stderr)
        sys.exit(1)

    if args.mode == "once":
        run_once(cfg)
    else:
        print("Modo contínuo (Ctrl+C para parar). Paper only, sem risco real.")
        try:
            while True:
                run_once(cfg)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nEncerrado.")


if __name__ == "__main__":
    main()
