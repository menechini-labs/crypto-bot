"""Active coins management, per-coin risk config, per-coin default SL/TP/trailing."""

from __future__ import annotations

import os
import threading
from typing import Any

_DEFAULT_COINS = os.getenv('ACTIVE_COINS', 'BTCUSDT,ETHUSDT,SOLUSDT').split(',')
_ACTIVE_COINS: list[str] = [c.strip() for c in _DEFAULT_COINS if c.strip()]
_COIN_CONFIG: dict[str, dict[str, Any]] = {}
_LOCK = threading.RLock()


def get_active_coins() -> list[str]:
    with _LOCK:
        return list(_ACTIVE_COINS)


def set_active_coins(coins: list[str]) -> None:
    with _LOCK:
        _ACTIVE_COINS.clear()
        _ACTIVE_COINS.extend(coins)
        for sym in list(_COIN_CONFIG.keys()):
            if sym not in _ACTIVE_COINS:
                del _COIN_CONFIG[sym]


def add_coin(symbol: str) -> None:
    with _LOCK:
        if symbol not in _ACTIVE_COINS:
            _ACTIVE_COINS.append(symbol)


def remove_coin(symbol: str) -> None:
    with _LOCK:
        if symbol in _ACTIVE_COINS:
            _ACTIVE_COINS.remove(symbol)
        _COIN_CONFIG.pop(symbol, None)


def get_coin_config(symbol: str) -> dict[str, Any]:
    with _LOCK:
        cfg = _COIN_CONFIG.get(symbol, {})
    return {
        'symbol': symbol,
        'sl_pct': cfg.get('sl_pct', 0.02),
        'tp_pct': cfg.get('tp_pct', 0.05),
        'trailing_pct': cfg.get('trailing_pct', 0.01),
        'auto_trade': cfg.get('auto_trade', False),
    }


def set_coin_config(symbol: str, config: dict[str, Any]) -> None:
    with _LOCK:
        cur = _COIN_CONFIG.get(symbol, {})
        cur.update(config)
        _COIN_CONFIG[symbol] = cur


def list_coin_configs() -> list[dict[str, Any]]:
    with _LOCK:
        return [get_coin_config(sym) for sym in _ACTIVE_COINS]
