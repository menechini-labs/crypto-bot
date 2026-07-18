# core/strategy_registry/__init__.py
"""Strategy Registry Package - Plugin-style strategies."""

# Import all strategies to register them
from . import (  # noqa: F401
    breakout_strategy,
    contrarian_strategy,
    dynamic_grid_strategy,
    grid_strategy,
    indicator_strategies,
    llm_strategy,
    mean_reversion_strategy,
    range_bound_strategy,
    scalping_strategy,
)
from .base import BaseStrategy
from .registry import get, get_all, register

__all__ = ['BaseStrategy', 'register', 'get', 'get_all']
