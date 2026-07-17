# core/market_ws.py
"""WebSocket market client for Binance klines with strategy integration."""
import asyncio
import json
import logging
from typing import Optional

import websockets

from .scoring import calculate_volatility, detect_regime, support_resistance
from .strategy_registry import get_all
from .strategy_registry.base import BaseStrategy
from .reporter import append_equity, latest_equity, load_history

log = logging.getLogger(__name__)


class WebSocketMarket:
    """WebSocket client for Binance klines stream."""

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        cache_limit: int = 200,
        strategy_name: str | None = None,
    ):
        self.symbol = symbol
        self.interval = interval
        self.cache_limit = cache_limit
        self.strategy_name = strategy_name
        self.ws_url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{interval}"
        self.cache: list[dict] = []
        self.running = False
        self._task: Optional[asyncio.Task] = None

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
                if payload.get("e") != "kline":
                    continue

                k = payload["k"]
                candle = {
                    "ts": k["t"],
                    "open": float(k["o"]),
                    "high": float(k["h"]),
                    "low": float(k["l"]),
                    "close": float(k["c"]),
                    "volume": float(k["v"]),
                }
                self.cache.append(candle)
                if len(self.cache) > self.cache_limit:
                    self.cache.pop(0)

                # Build context for strategies
                closes = [c["close"] for c in self.cache]
                vol = calculate_volatility(closes)
                regime = detect_regime(closes)
                sup, res = support_resistance(closes)
                ctx = {
                    "symbol": self.symbol,
                    "volatility": round(vol, 2),
                    "regime": regime,
                    "support": sup,
                    "resistance": res,
                }

                # Dispatch to strategies (plugin-style)
                strategies = get_all()
                for name, strat_cls in strategies.items():
                    if self.strategy_name and name != self.strategy_name:
                        continue
                    strategy = strat_cls()
                    if hasattr(strategy, "on_new_candle"):
                        asyncio.create_task(strategy.on_new_candle(self.cache))
                    else:
                        # Synchronous decide for non-async strategies
                        signal = strategy.decide(closes[-10:], has_position=False, ctx=ctx)
                        log.info("Strategy %s signal: %s", name, signal)

                await asyncio.sleep(0)
                log.debug("Cycle processed; cache len=%d", len(self.cache))
            except websockets.ConnectionClosed as e:
                log.warning("WS closed: %s - reconnecting", e)
                self.running = False
                await asyncio.sleep(5)
                await self.connect()
            except Exception as exc:
                log.exception("WS error: %s - restarting", exc)
                self.running = False
                await asyncio.sleep(5)
                await self.connect()

    async def stop(self) -> None:
        """Gracefully shutdown WS loop."""
        self.running = False
        if self._task:
            self._task.cancel()
        if hasattr(self, "websocket"):
            await self.websocket.close()

    async def get_latest(self) -> Optional[dict]:
        """Return most recent candle if cached."""
        return self.cache[-1] if self.cache else None
