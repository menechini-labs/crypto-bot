# core/market_ws.py
import asyncio
import json
import logging
from typing import Optional

import websockets
from urllib.parse import urljoin

from .. import config
from ..core.registry import StrategyRegistry
from ..risk import RiskEngine
from ..reporter import Reporter

log = logging.getLogger(__name__)

class WebSocketMarket:
    """WebSocket client for Binance klines stream."""
    def __init__(self,
                 symbol: str = "BTCUSDT",
                 interval: str = "1h",
                 cache_limit: int = 200):
        self.symbol = symbol
        self.interval = interval
        self.cache_limit = cache_limit
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
                if payload["e"] != "kline":
                    continue
                candle = {
                    "ts": payload["k"]["t"],
                    "open": payload["k"]["o"],
                    "high": payload["k"]["h"],
                    "low": payload["k"]["l"],
                    "close": payload["k"]["c"],
                    "volume": payload["k"]["v"]
                }
                self.cache.append(candle)
                if len(self.cache) > self.cache_limit:
                    self.cache.pop(0)
                # fire events for strategies / risk
                for strategy in StrategyRegistry.get_all():
                    asyncio.create_task(strategy.on_new_candle(self.cache))
                await Reporter.update_metrics(self.cache[-1])
            except websockets.ConnectionClosed as e:
                log.warning("WS closed: %s – reconnecting", e)
                self.running = False
                await asyncio.sleep(5)
                await self.connect()
            except Exception as exc:
                log.exception("WS error: %s – restarting", exc)
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