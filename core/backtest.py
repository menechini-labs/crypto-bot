"""Engine de backtest (stdlib, sem look-ahead).

Aplica uma estratégia sobre um histórico de closes, candle a candle.
No passo t, a decisão usa APENAS closes[0..t] (sem olhar o futuro).
Usa PaperWallet + PaperExecutor (paper only, sem ordem real).
"""
from core.wallet import PaperWallet
from core.risk import RiskManager
from core.execution import PaperExecutor
from core.metrics import compute_metrics


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
    """Retorna relatório: final_equity, pnl, trades, win_rate, max_drawdown_pct."""
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
    dynamic_center = None
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
        dynamic_center = initial_center

    initial = cfg["initial_cash_usdt"]
    trades = 0
    wins = 0
    peak = initial
    max_dd = 0.0
    equity_curve: list[float] = [initial]

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
            if risk.should_stop_loss(entry, price):
                gross = wallet.position_value(symbol, price)
                wallet.sell(symbol, price)
                trades += 1
                if price >= entry:
                    wins += 1
            elif risk.should_take_profit(entry, price):
                wallet.sell(symbol, price)
                trades += 1
                if price >= entry:
                    wins += 1
        elif signal == "buy":
            notional = risk.max_notional(wallet.cash)
            if notional > 0:
                executor.execute_buy(symbol, price, notional)
                wallet.buy(symbol, price, notional)
                trades += 1

        equity = wallet.equity({symbol: price})
        equity_curve.append(equity)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    final_equity = wallet.equity({symbol: closes[-1]})
    # fecha posição remanescente para apurar PnL real
    if symbol in wallet.positions:
        wallet.sell(symbol, closes[-1])
    final_equity = wallet.equity({})

    pnl = final_equity - initial
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
        "pnl": pnl,
        "pnl_pct": (pnl / initial) if initial > 0 else 0.0,
        "max_drawdown_pct": max_dd,
        "sharpe": metrics["sharpe"],
        "cagr": metrics["cagr"],
    }
