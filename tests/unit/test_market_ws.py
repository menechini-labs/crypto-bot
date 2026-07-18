import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.frames import Close

from core.market_ws import WebSocketMarket


@pytest.mark.asyncio
async def test_websocket_connect_success():
    mock_ws = AsyncMock()
    mock_ws.__aenter__.return_value = mock_ws
    mock_ws.__aexit__.return_value = None
    with patch('websockets.connect', new=AsyncMock(return_value=mock_ws)) as mock_connect:
        market = WebSocketMarket(symbol='BTCUSDT', interval='1m')
        await market.connect()
        assert market.running is True
        mock_connect.assert_called_once_with('wss://stream.binance.com:9443/ws/btcusdt@kline_1m')


@pytest.mark.asyncio
async def test_websocket_receive_loop():
    market = WebSocketMarket()
    mock_ws = AsyncMock()
    mock_ws.recv = AsyncMock(
        side_effect=[
            json.dumps(
                {
                    'e': 'kline',
                    'k': {
                        't': 1609459200000,
                        'o': '100.0',
                        'h': '110.0',
                        'l': '90.0',
                        'c': '105.0',
                        'v': '10.0',
                    },
                }
            ),
            ConnectionClosed(rcvd=Close(1000, 'norm'), sent=None),
        ]
    )
    mock_ws.__aiter__.return_value = []
    with patch('websockets.connect', new=AsyncMock(return_value=mock_ws)):
        await market.connect()
        # let task run briefly
        await asyncio.sleep(0.1)
        assert market.running is False  # because connection closed after one msg
        assert len(market.cache) == 1
        candle = market.cache[0]
        assert candle['close'] == 105.0


@pytest.mark.asyncio
async def test_get_latest():
    market = WebSocketMarket()
    assert (await market.get_latest()) is None
    market.cache.append({'ts': 1, 'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1})
    latest = await market.get_latest()
    assert latest is not None
    assert latest['close'] == 1
