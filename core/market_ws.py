# core/market_ws.py
"""WebSocket market client for Binance klines with strategy integration."""

import asyncio
import json
import logging
from collections.abc import Callable

import websockets

from .scoring import calculate_volatility, detect_regime, support_resistance
from .strategy_registry import get_all

log = logging.getLogger(__name__)


class WebSocketMarket:
    """WebSocket client for Binance klines stream."""

    def __init__(
        self,
        symbol: str = 'BTCUSDT',
        interval: str = '1h',
        cache_limit: int = 200,
        strategy_name: str | None = None,
    ):
        self.symbol = symbol
        self.interval = interval
        self.cache_limit = cache_limit
        self.strategy_name = strategy_name
        self.ws_url = f'wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{interval}'
        self.cache: list[dict] = []
        self.running = False
        self._task: asyncio.Task | None = None
        # Hook opcional: callable(candle) chamado a cada vela recebida (fechada ou não).
        self.candle_listener: Callable[[dict], None] | None = None
        self._event_bus = None  # Lazy import no _receive_loop

    async def connect(self) -> None:
        """Establish WS connection and start background receive loop."""
        self.websocket = await websockets.connect(self.ws_url)
        self.running = True
        self._task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        """Consume messages, cache, fire strategy signals."""
        while self.running:
            try:
                raw = await self.websocket.recv()
                payload = json.loads(raw)
                if payload.get('e') != 'kline':
                    continue

                k = payload['k']
                candle = {
                    'ts': k['t'],
                    'open': float(k['o']),
                    'high': float(k['h']),
                    'low': float(k['l']),
                    'close': float(k['c']),
                    'volume': float(k['v']),
                }
                self.cache.append(candle)
                if len(self.cache) > self.cache_limit:
                    self.cache.pop(0)

                # Hook opcional: notifica qualquer ouvinte (ex.: motor de sinais 1m).
                if self.candle_listener is not None:
                    try:
                        self.candle_listener(candle)
                    except Exception as exc:  # nunca derruba o loop WS
                        log.warning('candle_listener error: %s', exc)

                # Build context for strategies
                closes = [c['close'] for c in self.cache]
                vol = calculate_volatility(closes)
                regime = detect_regime(closes)
                sup, res = support_resistance(closes)
                ctx = {
                    'symbol': self.symbol,
                    'volatility': round(vol, 2),
                    'regime': regime,
                    'support': sup,
                    'resistance': res,
                }

                # Event bus dispatch
                if self._event_bus is not None:
                    event = {
                        'type': 'candle',
                        'symbol': self.symbol,
                        'candle': candle,
                        'ctx': ctx,
                    }
                    await self._event_bus.emit('candle', event)

                # Dispatch to strategies (plugin-style) somente quando um
                # strategy_name explícito é informado (evita auto-fire global).
                if self.strategy_name is not None:
                    from .event_bus import get_global_bus

                    self._event_bus = get_global_bus()

                    strategies = get_all()
                    for name, strat_cls in strategies.items():
                        if name != self.strategy_name:
                            continue
                        strategy = strat_cls()
                        if hasattr(strategy, 'on_new_candle'):
                            asyncio.create_task(strategy.on_new_candle(self.cache))
                        else:
                            signal = strategy.decide(closes[-10:], has_position=False, ctx=ctx)
                            log.info('Strategy %s signal: %s', name, signal)

                            # Track signal_str from the matched strategy
                            if signal:
                                signal_str = signal.get('signal', 'hold') if isinstance(signal, dict) else str(signal)

                    # Emit signal event
                    if signal_str and self._event_bus is not None:
                        sig_event = {
                            'type': 'signal',
                            'symbol': self.symbol,
                            'strategy': self.strategy_name,
                            'signal': signal_str,
                            'ctx': ctx,
                        }
                        await self._event_bus.emit('signal', sig_event)

                await asyncio.sleep(0)
                log.debug('Cycle processed; cache len=%d', len(self.cache))
            except websockets.ConnectionClosed as e:
                log.warning('WS closed: %s - reconnecting', e)
                self.running = False
                await asyncio.sleep(5)
                await self.connect()
            except Exception:
                log.exception('WS error - restarting')
                self.running = False
                await asyncio.sleep(5)
                await self.connect()

    async def stop(self) -> None:
        """Gracefully shutdown WS loop."""
        self.running = False
        if self._task:
            self._task.cancel()
        if hasattr(self, 'websocket'):
            await self.websocket.close()

    async def get_latest(self) -> dict | None:
        """Return most recent candle if cached."""
        return self.cache[-1] if self.cache else None
