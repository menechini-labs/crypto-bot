#!/usr/bin/env python3
"""AI-Trader Heartbeat Watcher — async.

Polls ai4trade.ai heartbeat, emits notifications to our EventBus.
"""
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus
from core.ai_trader_client import get_ai_trader_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("ai_trader_hb")

POLL_INTERVAL = 30
MAX_CONSECUTIVE_ERRORS = 10


async def process_heartbeat(event_bus: EventBus) -> bool:
    try:
        client = get_ai_trader_client()
        if not client.config.token or not client.config.enabled:
            logger.warning("AI-Trader not configured; skip heartbeat")
            return False

        hb = client.heartbeat()
        if hb.message_count > 0 or hb.tasks:
            logger.info("Heartbeat: %d messages, %d tasks, %d unread", hb.message_count, len(hb.tasks), hb.unread_count)

        for msg in hb.messages:
            msg_type = msg.get("type", "unknown")
            content = msg.get("content", "")
            data = msg.get("data", {})
            logger.info("HB msg [%s]: %s", msg_type, content[:120])
            await event_bus.emit("ai_trader.notification", {"type": msg_type, "content": content, "data": data, "source": "ai4trade.ai"})

        for task in hb.tasks:
            task_type = task.get("type", "unknown")
            input_data = task.get("input_data", {})
            logger.info("HB task [%s]: %s", task_type, str(input_data)[:120])
            await event_bus.emit("ai_trader.task", {"type": task_type, "input_data": input_data, "source": "ai4trade.ai"})

        if hb.has_more_messages:
            logger.info("More messages available")

        return True
    except Exception as e:
        logger.error("Heartbeat poll failed: %s", e)
        return False


async def run_forever():
    event_bus = EventBus()
    errors = 0
    logger.info("AI-Trader Heartbeat Watcher started (interval=%ds)", POLL_INTERVAL)
    while True:
        ok = await process_heartbeat(event_bus)
        if ok:
            errors = 0
        else:
            errors += 1
            if errors >= MAX_CONSECUTIVE_ERRORS:
                logger.error("%d consecutive errors; giving up", errors)
                break
        await asyncio.sleep(POLL_INTERVAL)


async def run_once():
    event_bus = EventBus()
    await process_heartbeat(event_bus)


if __name__ == "__main__":
    if "--once" in sys.argv:
        asyncio.run(run_once())
    else:
        asyncio.run(run_forever())
