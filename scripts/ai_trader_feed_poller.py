#!/usr/bin/env python3
"""AI-Trader Feed Poller — async periodic signal feed ingestion."""
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_trader_client import get_ai_trader_client
from core.event_bus import EventBus

logger = logging.getLogger("ai_trader_feed")

POLL_INTERVAL = 300
MAX_SIGNALS = 20


async def poll_and_score():
    try:
        client = get_ai_trader_client()
        if not client.config.token:
            logger.debug("AI-Trader not configured; skip feed")
            return False

        feed = client.get_feed(limit=MAX_SIGNALS, sort="new")
        if not feed:
            logger.debug("No new signals in feed")
            return True

        logger.info("Fetched %d signals from AI-Trader feed", len(feed))
        event_bus = EventBus()

        for signal in feed:
            await event_bus.emit("ai_trader.signal", {
                "id": signal.id,
                "agent": signal.agent_name,
                "type": signal.type,
                "symbol": signal.symbol,
                "side": signal.side,
                "price": signal.entry_price,
                "content": signal.content[:150],
                "source": "ai4trade.ai",
            })

            if signal.type in ("position", "trade") and signal.symbol:
                await event_bus.emit("scoring.external_signal", {
                    "agent": signal.agent_name,
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "entry_price": signal.entry_price,
                    "type": signal.type,
                    "timestamp": signal.timestamp,
                })

        return True
    except Exception as e:
        logger.error("Feed poll failed: %s", e)
        return False


async def run_forever():
    logger.info("AI-Trader Feed Poller started (interval=%ds)", POLL_INTERVAL)
    while True:
        await poll_and_score()
        await asyncio.sleep(POLL_INTERVAL)


async def run_once():
    await poll_and_score()


if __name__ == "__main__":
    if "--once" in sys.argv:
        asyncio.run(run_once())
    else:
        asyncio.run(run_forever())
