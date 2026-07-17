"""Prompt templates for LLM-driven strategy (stdlib-only, no external deps)."""

# Analyzes market and returns a single discrete signal.
DEFAULT_LLM_PROMPT = """
You are a crypto day-trading analyst. Analyze the data and reply with ONE word only.

=== Market Data ===
Symbol: {symbol}
Latest price: {latest_price}
Price change (last 10 candles): {price_change_pct}%
Volume: {volume}
Recent closes:
{candles}

=== Context ===
Position: {position_status}
Risk tolerance: {risk_tolerance}
Market regime: {market_regime}
Support: {support} | Resistance: {resistance}
Volatility (ATR %): {volatility}%

=== Rules ===
1. Use trend + momentum (SMA20 vs SMA50, RSI, last 3 candles).
2. Only BUY if price near support and RSI < 70 and regime != strong_downtrend.
3. Only SELL if price near resistance and RSI > 30 and regime != strong_uptrend.
4. HOLD if ambiguous or volatility > 5%.

Reply exactly: BUY, SELL, or HOLD. No explanation.
"""

# Validates a proposed trade against hard guardrails.
RISK_GUARD_PROMPT = """
You are a risk guard. Validate this proposed trade.

Symbol: {symbol}
Entry: {entry_price}
Stop-loss: {sl_pct}% | Take-profit: {tp_pct}%
Position size % of cash: {position_pct}%
Available cash: {available_cash}
Max allowed position %: {max_position_pct}%
Volatility: {volatility}% (max {vol_threshold}%)
Open positions: {open_positions} (max {max_open_positions})

Checks:
1. position_pct <= max_position_pct
2. sl_pct <= tp_pct (risk/reward >= 1)
3. volatility <= vol_threshold
4. open_positions < max_open_positions

Reply exactly: ALLOW, or REJECT: <one-sentence reason>.
"""


def get_prompt(name: str) -> str:
    """Return prompt template by name."""
    if name == "default_llm":
        return DEFAULT_LLM_PROMPT
    if name == "risk_guard":
        return RISK_GUARD_PROMPT
    raise ValueError(f"Unknown prompt name: {name}")
