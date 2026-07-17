# core/strategy_registry/registry.py
"""Strategy registry (plugin-style)."""
from .base import BaseStrategy
from typing import Dict, Type


_STRATEGIES: Dict[str, Type[BaseStrategy]] = {}


def register(name: str):
    """Decorator to register a strategy class."""
    def decorator(cls: Type[BaseStrategy]):
        if not issubclass(cls, BaseStrategy):
            raise TypeError(f"Registered class {cls} must inherit BaseStrategy")
        _STRATEGIES[name] = cls
        return cls
    return decorator


def get(name: str) -> Type[BaseStrategy]:
    """Return strategy class by name."""
    try:
        return _STRATEGIES[name]
    except KeyError:
        raise KeyError(f"Strategy '{name}' not registered. Available: {list(_STRATEGIES)}")


def get_all() -> Dict[str, Type[BaseStrategy]]:
    """Return a copy of the registry."""
    return dict(_STRATEGIES)