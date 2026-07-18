"""Event Bus — pub/sub assíncrono para eventos de mercado.

Usado pelo WebSocketMarket para dispatch de eventos
para listeners registrados (signals, candles, regime change).

Nenhuma dependência externa.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

EventHandler = Callable[..., Any] | Callable[..., Coroutine[Any, Any, None]]


@dataclass(frozen=True)
class Event:
    type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Pub/sub event bus thread-safe para ambiente asyncio.

    Uso:
        bus = EventBus()
        bus.on('candle', my_handler)
        await bus.emit('candle', {'symbol': 'BTCUSDT', ...})
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Registra handler para um tipo de evento."""
        self._handlers.setdefault(event_type, []).append(handler)
        log.debug('EventBus: registered handler for %s (total=%d)', event_type, len(self._handlers[event_type]))

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Remove handler registration."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            log.debug('EventBus: removed handler for %s', event_type)

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Dispara evento para todos os handlers registrados.

        Handlers síncronos são executados via asyncio.to_thread.
        Handlers assíncronos aguardados com gather.
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return

        event = Event(type=event_type, data=data)

        coros: list[asyncio.coroutine] = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                coros.append(handler(event))
            else:
                try:
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, handler, event)
                except RuntimeError:
                    handler(event)

        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    def clear(self) -> None:
        """Remove todos os handlers registrados."""
        self._handlers.clear()


# Singleton global
_global_bus: EventBus | None = None


def get_global_bus() -> EventBus:
    """Retorna o EventBus global (singleton)."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus
