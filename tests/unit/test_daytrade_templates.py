"""Unit tests for day-trade platform improvements.

Cobre:
  - Indicadores intraday (vwap, atr, stochastic) — stdlib, retornam finitos.
  - Estratégias-template (scalping, breakout, mean_reversion, range_bound, contrarian).
  - Correção do bug grid_dynamic (sem NameError em ccloses/closes).
"""

import math
from typing import Any, cast

import pytest

from core import indicators as ind
from core.strategy_registry import get, get_all


def _finite(x) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


# ── Indicadores ──────────────────────────────────────────────────────
def _synthetic(n=60):
    """Série OHLCV sintética subindo com ruído."""
    hs, ls, cs, vs = [], [], [], []
    price = 100.0
    for i in range(n):
        price += (i % 5 - 2) * 0.5 + 0.1
        c = round(price, 2)
        h = round(c + 1.0, 2)
        lo = round(c - 1.0, 2)
        v = 1000 + (i % 7) * 50
        hs.append(h)
        ls.append(lo)
        cs.append(c)
        vs.append(float(v))
    return hs, ls, cs, vs


def test_vwap_finite():
    hs, ls, cs, vs = _synthetic()
    v = ind.vwap(hs, ls, cs, vs)
    assert _finite(v)
    assert v is not None
    assert v > 0


def test_vwap_empty_returns_none():
    assert ind.vwap([], [], [], []) is None


def test_atr_finite():
    hs, ls, cs, vs = _synthetic()
    a = ind.atr(hs, ls, cs, period=14)
    assert _finite(a)
    assert a is not None
    assert a > 0


def test_atr_insufficient_returns_none():
    hs, ls, cs, vs = _synthetic(10)
    assert ind.atr(hs, ls, cs, period=14) is None


def test_stochastic_finite():
    hs, ls, cs, vs = _synthetic()
    st = ind.stochastic(cs, hs, ls, period=14, smooth=3)
    assert isinstance(st, dict)
    assert 'k' in st and 'd' in st
    assert _finite(st['k']) and _finite(st['d'])
    assert 0 <= st['k'] <= 100
    assert 0 <= st['d'] <= 100


def test_stochastic_short_returns_none():
    st = ind.stochastic([1, 2, 3], [1, 2, 3], [0.5, 1.5, 2.5], period=14)
    assert st['k'] is None and st['d'] is None


# ── Estratégias-template ──────────────────────────────────────────────
TEMPLATE_NAMES = ['scalping', 'breakout', 'mean_reversion', 'range_bound', 'contrarian']


def _candles(n=60):
    hs, ls, cs, vs = _synthetic(n)
    return [
        {'high': hs[i], 'low': ls[i], 'close': cs[i], 'volume': vs[i], 'ts': i} for i in range(n)
    ]


@pytest.mark.parametrize('name', TEMPLATE_NAMES)
def test_template_registered(name):
    assert name in get_all()


@pytest.mark.parametrize('name', TEMPLATE_NAMES)
def test_template_decide_returns_signal_dict(name):
    strat = get(name)()
    candles: list[dict[str, Any]] = _candles()
    ctx = {'symbol': 'BTCUSDT', 'candles': candles}
    sig = strat.decide([c['close'] for c in candles], has_position=False, ctx=ctx)
    assert isinstance(sig, dict)
    sig_d = cast('dict[str, Any]', sig)
    assert 'side' in sig_d
    assert sig_d['side'] in ('buy', 'sell', 'hold')
    assert 'confidence' in sig_d
    assert _finite(sig_d['confidence'])
    assert 0.0 <= sig_d['confidence'] <= 1.0
    assert 'reason' in sig_d


@pytest.mark.parametrize('name', TEMPLATE_NAMES)
def test_template_no_crash_with_position(name):
    strat = get(name)()
    candles = _candles()
    ctx = {'symbol': 'BTCUSDT', 'candles': candles}
    sig = strat.decide([c['close'] for c in candles], has_position=True, ctx=ctx)
    assert isinstance(sig, dict)
    assert sig.get('side') in ('buy', 'sell', 'hold')


# ── Correção grid_dynamic (bug ccloses/closes) ────────────────────────
def test_grid_dynamic_no_name_error():
    strat = get('grid_dynamic')()
    closes = [100.0, 101.0, 102.0, 103.0, 104.0]
    # Não deve levantar NameError (ccloses/closes indefinidos)
    sig = strat.decide(closes, has_position=False)
    assert sig in ('buy', 'sell', 'hold')


def test_grid_dynamic_with_position():
    strat = get('grid_dynamic')()
    closes = [100.0, 101.0, 99.0, 98.0, 97.0]
    sig = strat.decide(closes, has_position=True)
    assert sig in ('buy', 'sell', 'hold')


# ── Swarm presets day-trade ───────────────────────────────────────────
def test_daytrade_presets_exist():
    from core.swarm_presets import get_preset

    for name in [
        'daytrade_scalping',
        'daytrade_breakout',
        'daytrade_mean_reversion',
        'daytrade_range_bound',
        'daytrade_contrarian',
    ]:
        p = get_preset(name)
        assert p is not None, f'preset {name} ausente'
        assert p['behaviors']['strategy'] in TEMPLATE_NAMES


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
