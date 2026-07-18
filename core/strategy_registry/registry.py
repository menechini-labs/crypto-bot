# core/strategy_registry/registry.py
"""Strategy registry (plugin-style)."""

from .base import BaseStrategy

_STRATEGIES: dict[str, type[BaseStrategy]] = {}


def register(name: str):
    """Decorator to register a strategy class."""

    def decorator(cls: type[BaseStrategy]):
        if not issubclass(cls, BaseStrategy):
            raise TypeError(f'Registered class {cls} must inherit BaseStrategy')
        _STRATEGIES[name] = cls
        return cls

    return decorator


def get(name: str) -> type[BaseStrategy]:
    """Return strategy class by name."""
    try:
        return _STRATEGIES[name]
    except KeyError as err:
        raise KeyError(f"Strategy '{name}' not registered. Available: {list(_STRATEGIES)}") from err


def get_all() -> dict[str, type[BaseStrategy]]:
    """Return a copy of the registry."""
    return dict(_STRATEGIES)
