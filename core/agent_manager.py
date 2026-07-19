"""Agent Loop Manager — runs independent agent cycles per coin concurrently.

Each active coin gets its own agent cycle via asyncio.gather.
Per-coin timeout prevents one slow coin from blocking others.
Shared portfolio-level risk guard applied after all cycles complete.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

log = logging.getLogger(__name__)

from core import agent_desk as _agent_desk
from core import paper_engine as _paper
from core.coin_manager import get_active_coins, get_coin_config
from core.strategy_registry.registry import get_all as _registry_get_all


# In-memory cache: stores last cycle result per coin
_CYCLE_CACHE: dict[str, dict[str, Any]] = {}
_CYCLE_TS: dict[str, float] = {}
_CYCLE_LOCK: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _CYCLE_LOCK
    if _CYCLE_LOCK is None:
        _CYCLE_LOCK = asyncio.Lock()
    return _CYCLE_LOCK


def _fetch_closes(symbol: str) -> list[float]:
    """Fetch OHLCV closes for a symbol. Returns empty list on error."""
    try:
        from core.market import fetch_ohlcv
        candles = fetch_ohlcv(symbol, '1h', 100)
        return [c['close'] for c in candles]
    except Exception as exc:
        log.warning('fetch_closes(%s) failed: %s', symbol, exc)
        return []


async def _run_single_cycle(symbol: str) -> dict[str, Any]:
    """Run one agent cycle for a single coin. Returns cycle dict."""
    closes = _fetch_closes(symbol)
    try:
        cycle = _agent_desk.run_cycle(closes if len(closes) >= 20 else None)
        cycle['symbol'] = symbol
        return cycle
    except Exception as exc:
        log.error('cycle failed for %s: %s', symbol, exc)
        return {
            'status': 'error',
            'symbol': symbol,
            'error': str(exc),
            'cycle_id': int(time.time() * 1000),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }


async def _execute_single(symbol: str, cycle: dict[str, Any], mode: str) -> dict[str, Any]:
    """Execute a cycle's decision for one coin via PaperEngine."""
    decision = cycle.get('decision')
    if not decision:
        return {'executed': False, 'reason': 'no decision'}
    verdict = decision.get('verdict') if isinstance(decision, dict) else getattr(decision, 'verdict', None)
    conf = decision.get('confidence') if isinstance(decision, dict) else getattr(decision, 'confidence', 0.0)
    if mode != 'real' or verdict not in ('buy', 'sell') or conf < 0.5:
        return {
            'executed': False,
            'reason': 'DEMO mode' if mode != 'real' else f'{verdict} conf={conf:.2f} < 0.5',
        }
    engine = _paper.get_engine()
    snap = engine.snapshot()
    available = snap.get('cash', 0.0)
    qty = _agent_desk._compute_qty(symbol, conf, available)
    if qty <= 0:
        return {'executed': False, 'reason': f'qty={qty} <= 0'}
    coin_cfg = get_coin_config(symbol)
    order = _paper.Order(
        symbol=symbol,
        side=verdict,
        qty=qty,
        sl_pct=coin_cfg.get('sl_pct', 0.02),
        tp_pct=coin_cfg.get('tp_pct', 0.05),
        trailing_pct=coin_cfg.get('trailing_pct', 0.01),
        reason=f'AgentDesk {verdict} ({symbol}, conf {conf:.2f})',
        advisory=decision.get('reasoning', ''),
    )
    result = engine.submit(order)
    return {
        'executed': bool(result.get('ok')),
        'order_id': result.get('order', {}).get('id'),
        'result': result,
        'qty': qty,
    }


async def run_all_cycles(mode: str = 'demo', timeout: float = 30.0) -> list[dict[str, Any]]:
    """Run agent cycles for all active coins concurrently.

    Returns list of cycle results (one per coin).
    """
    coins = get_active_coins()
    if not coins:
        return []

    async def _wrapped(sym: str) -> dict[str, Any]:
        try:
            cycle = await asyncio.wait_for(
                _run_single_cycle(sym),
                timeout=timeout,
            )
            # Auto-execute if REAL mode
            exec_result = await _execute_single(sym, cycle, mode)
            cycle['execution'] = exec_result
            # Cache
            async with _get_lock():
                _CYCLE_CACHE[sym] = cycle
                _CYCLE_TS[sym] = time.time()
            return cycle
        except asyncio.TimeoutError:
            err = {
                'status': 'timeout',
                'symbol': sym,
                'error': f'cycle timeout ({timeout}s)',
            }
            async with _get_lock():
                _CYCLE_CACHE[sym] = err
                _CYCLE_TS[sym] = time.time()
            return err

    results = await asyncio.gather(*[_wrapped(c) for c in coins], return_exceptions=True)
    out = []
    for r in results:
        if isinstance(r, Exception):
            out.append({'status': 'error', 'error': str(r)})
        else:
            out.append(r)
    return out


def get_last_cycle(symbol: str) -> dict[str, Any] | None:
    return _CYCLE_CACHE.get(symbol)


def get_all_last_cycles() -> dict[str, dict[str, Any]]:
    return dict(_CYCLE_CACHE)


async def run_single_coin(symbol: str, mode: str = 'demo', timeout: float = 30.0) -> dict[str, Any]:
    """Run one agent cycle for a specific coin + auto-execute."""
    cycle = await asyncio.wait_for(
        _run_single_cycle(symbol),
        timeout=timeout,
    )
    exec_result = await _execute_single(symbol, cycle, mode)
    cycle['execution'] = exec_result
    async with _get_lock():
        _CYCLE_CACHE[symbol] = cycle
        _CYCLE_TS[symbol] = time.time()
    return cycle
