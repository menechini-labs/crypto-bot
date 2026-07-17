"""Engine de backtest (stdlib, sem look-ahead).

Aplica uma estratégia sobre um histórico de closes, candle a candle.
No passo t, a decisão usa APENAS closes[0..t] (sem olhar o futuro).
Usa PaperWallet + PaperExecutor (paper only, sem ordem real).
"""
import logging

logger = logging.getLogger("crypto-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


from core.execution import PaperExecutor
from core.metrics import compute_metrics
from core.risk import RiskManager
from core.wallet import PaperWallet


def _strategy_signal(strategy_name: str, closes: list[float], grid_levels=None, has_position=False) -> str:
    if strategy_name == "always_buy":
        return "buy"
    if strategy_name == "always_hold":
        return "hold"
    if strategy_name == "grid":
        from core.strategy import decide_grid
        return decide_grid(closes, grid_levels, has_position)
    # estratégia real do bot
    from core.strategy import decide
    return decide(closes)


def run_backtest(
    closes: list[float],
    cfg: dict,
    symbol: str = "BACKTEST/USDT",
    strategy_name: str = "default",
) -> dict:
    logger.info("run_backtest symbol=%s strategy=%s n=%d", symbol, strategy_name, len(closes))
    """Retorna relatório: final_equity, pnl, trades, win_rate, max_drawdown_pct,
    equity_curve e lista de trades."""
    wallet = PaperWallet(initial_cash=cfg["initial_cash_usdt"], fee_pct=cfg["fee_pct"])
    risk = RiskManager(
        max_position_pct=cfg["max_position_pct"],
        stop_loss_pct=cfg["stop_loss_pct"],
        take_profit_pct=cfg["take_profit_pct"],
    )
    executor = PaperExecutor(mode="paper")

    # niveis de grid derivados do range dos dados (janela deslizante nao usada aqui;
    # usa o range global para definir a grade de operacao em lateral)
    grid_levels = None
    if strategy_name == "grid":
        from core.strategy import build_grid
        lo, hi = min(closes), max(closes)
        # folga de 2% para nao operar nas bordas extremas
        lo, hi = lo * 1.02, hi * 0.98
        grid_levels = build_grid(lo, hi, n=10)
    elif strategy_name == "grid_dynamic":
        from core.strategy import build_dynamic_grid
        # centro inicial = media dos dados (recentralizado por ciclo)
        initial_center = sum(closes[:50]) / min(50, len(closes))
        grid_levels = build_dynamic_grid(center=initial_center, step=max(initial_center * 0.01, 1e-8), n=11)

    initial = cfg["initial_cash_usdt"]
    trades = 0
    wins = 0
    peak = initial
    max_dd = 0.0
    equity_curve: list[float] = [initial]
    trade_log: list[dict] = []
    _entry_price: float | None = None
    _entry_time: int | None = None
    _buy_price: float | None = None

    # precisamos de pelo menos 2 candles para um sinal
    for t in range(1, len(closes)):
        price = closes[t]
        window = closes[: t + 1]  # só dados ate o momento t (sem look-ahead)
        has_position = symbol in wallet.positions
        if strategy_name == "grid_dynamic":
            from core.strategy import build_dynamic_grid, decide_dynamic_grid
            # recentraliza o centro na media movel curta do preco
            center = window[-1]
            step = max(price * 0.01, 1e-8)  # 1% do preco por nivel
            grid_levels = build_dynamic_grid(center=center, step=step, n=11)
            signal = decide_dynamic_grid(window, grid_levels, has_position)
        else:
            signal = _strategy_signal(strategy_name, window, grid_levels, has_position)

        entry = wallet.positions.get(symbol, {}).get("avg_price")

        # gerencia risco em posição aberta
        if symbol in wallet.positions and entry:
            if risk.should_stop_loss(entry, price) or risk.should_take_profit(entry, price):
                side = "sell"
                exit_price = price
                pnl_trade = exit_price - entry
                pnl_trade_pct = pnl_trade / entry if entry else 0
                duration = t - (_entry_time or t)
                trade_log.append({
                    "side": side,
                    "entry_price": round(entry, 2),
                    "exit_price": round(exit_price, 2),
                    "pnl": round(pnl_trade, 2),
                    "pnl_pct": round(pnl_trade_pct, 4),
                    "duration_min": duration,
                })
                _entry_price = None
                _entry_time = None
                wallet.sell(symbol, price)
                trades += 1
                if price >= entry:
                    wins += 1
        elif signal == "buy" and _entry_price is None:
            notional = risk.max_notional(wallet.cash)
            if notional > 0:
                executor.execute_buy(symbol, price, notional)
                wallet.buy(symbol, price, notional)
                _entry_price = price
                _entry_time = t
                trades += 1

        equity = wallet.equity({symbol: price})
        equity_curve.append(equity)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    final_equity = wallet.equity({symbol: closes[-1]})
    # fecha posição remanescente para apurar PnL real
    if symbol in wallet.positions:
        wallet.sell(symbol, closes[-1])
    final_equity = wallet.equity({})

    pnl = final_equity - initial
    pnl_pct = pnl / initial if initial > 0 else 0.0
    win_rate = (wins / trades) if trades > 0 else 0.0

    metrics = compute_metrics(equity_curve, periods_per_year=365 * 24, wins=wins, trades=trades)

    return {
        "symbol": symbol,
        "strategy": strategy_name,
        "candles": len(closes),
        "trades": trades,
        "wins": wins,
        "win_rate": win_rate,
        "final_equity": final_equity,
        "equity": initial,
        "pnl": pnl,
        "pnl_pct": round(pnl_pct, 6),
        "max_drawdown_pct": round(max_dd, 6),
        "sharpe": round(metrics["sharpe"], 4),
        "cagr": round(metrics["cagr"], 6),
        "equity_curve": [round(e, 2) for e in equity_curve[1:]],
        "trades_list": trade_log,
    }
