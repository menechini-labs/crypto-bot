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
try:
    from core.scoring import score_signal, should_execute
except Exception:  # scoring opcional
    score_signal = None
    should_execute = None


def _strategy_signal(strategy_name: str, closes: list[float], grid_levels=None, has_position=False) -> str:
    if strategy_name == "always_buy":
        return "buy"
    if strategy_name == "always_hold":
        return "hold"
    if strategy_name == "grid":
        from core.strategy import decide_grid
        return decide_grid(closes, grid_levels, has_position)
    # tentar registry primeiro
    try:
        from core.strategy_registry.registry import get as _reg_get
        st = _reg_get(strategy_name)
        return st().decide(closes, has_position)
    except KeyError:
        pass
    # estratégia real do bot (fallback)
    from core.strategy import decide
    return decide(closes)


def run_backtest(
    closes: list[float],
    cfg: dict,
    symbol: str = "BACKTEST/USDT",
    strategy_name: str = "default",
    use_scoring: bool = True,
    strategy: object | None = None,
) -> dict:
    logger.info("run_backtest symbol=%s strategy=%s n=%d scoring=%s obj=%s", symbol, strategy_name, len(closes), use_scoring, strategy is not None)
    """Retorna relatório: final_equity, pnl, trades, win_rate, max_drawdown_pct,
    equity_curve e lista de trades.

    Com use_scoring=True, cada sinal de compra passa pelo score_signal +
    should_execute (confianca/risco) antes de ser executado.

    Se `strategy` (objeto com .decide(closes, has_position, ctx)) for passado,
    ele substitui o _strategy_signal por nome (ex.: LLMStrategy).
    """
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
    total_traded_notional: float = 0.0  # p/ turnover

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
            if strategy is not None:
                sctx = {
                    "symbol": symbol,
                    "regime": cfg.get("regime", "lateral"),
                    "volatility": cfg.get("volatility", 2.5),
                    "sl_pct": cfg.get("stop_loss_pct", 0.05) * 100,
                    "tp_pct": cfg.get("take_profit_pct", 0.10) * 100,
                }
                signal = strategy.decide(window, has_position, ctx=sctx)
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
            # Gate de scoring: so executa se confianca/risco aprovados
            if use_scoring and score_signal is not None and should_execute is not None:
                sctx = {
                    "symbol": symbol,
                    "regime": cfg.get("regime", "lateral"),
                    "volatility": cfg.get("volatility", 2.5),
                    "sl_pct": cfg.get("stop_loss_pct", 0.05) * 100,
                    "tp_pct": cfg.get("take_profit_pct", 0.10) * 100,
                }
                _score = score_signal(window, signal, has_position=False, ctx=sctx)
                if not should_execute(_score, min_confidence=0.4, min_risk=0.5):
                    logger.debug("buy rejeitado pelo scoring (conf=%.2f risk=%.2f)",
                                 _score.confidence, _score.risk_score)
                    continue
            notional = risk.max_notional(wallet.cash)
            if notional > 0:
                executor.execute_buy(symbol, price, notional)
                wallet.buy(symbol, price, notional)
                total_traded_notional += notional
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
        pos = wallet.positions[symbol]
        total_traded_notional += closes[-1] * pos["qty"]
        wallet.sell(symbol, closes[-1])
    final_equity = wallet.equity({})

    pnl = final_equity - initial
    pnl_pct = pnl / initial if initial > 0 else 0.0
    win_rate = (wins / trades) if trades > 0 else 0.0

    metrics = compute_metrics(
        equity_curve, periods_per_year=365 * 24, wins=wins, trades=trades, bootstrap=True
    )
    avg_equity = sum(equity_curve) / len(equity_curve) if equity_curve else initial
    turnover = (total_traded_notional / avg_equity) if avg_equity > 0 else 0.0

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
        "sharpe_ci": [round(x, 4) for x in metrics.get("sharpe_ci", [0.0, 0.0])],
        "turnover": round(turnover, 4),
        "cagr": round(metrics["cagr"], 6),
        "equity_curve": [round(e, 2) for e in equity_curve[1:]],
        "trades_list": trade_log,
    }
