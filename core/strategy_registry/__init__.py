# core/strategy_registry/__init__.py
"""Strategy Registry Package - Plugin-style strategies."""
from .base import BaseStrategy
from .registry import register, get, get_all

# Import all strategies to register them
from . import grid_strategy
from . import dynamic_grid_strategy
from . import llm_strategy

__all__ = ["BaseStrategy", "register", "get", "get_all"]