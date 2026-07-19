"""Tests for coin_manager and agent_manager (multi-coin Epics 2+3)."""

from __future__ import annotations

import pytest


class TestCoinManager:
    def test_default_coins(self):
        from core.coin_manager import get_active_coins

        coins = get_active_coins()
        assert len(coins) > 0
        assert 'BTCUSDT' in coins

    def test_set_active_coins(self):
        from core.coin_manager import set_active_coins, get_active_coins

        set_active_coins(['BTCUSDT', 'ETHUSDT'])
        assert get_active_coins() == ['BTCUSDT', 'ETHUSDT']

    def test_add_remove_coin(self):
        from core.coin_manager import add_coin, remove_coin, get_active_coins
        from core.coin_manager import set_active_coins

        set_active_coins(['BTCUSDT'])
        add_coin('SOLUSDT')
        assert 'SOLUSDT' in get_active_coins()
        remove_coin('SOLUSDT')
        assert 'SOLUSDT' not in get_active_coins()

    def test_coin_config_defaults(self):
        from core.coin_manager import set_active_coins, get_coin_config

        set_active_coins(['BTCUSDT'])
        cfg = get_coin_config('BTCUSDT')
        assert 'symbol' in cfg
        assert cfg['sl_pct'] == 0.02
        assert cfg['tp_pct'] == 0.05
        assert cfg['trailing_pct'] == 0.01
        assert cfg['auto_trade'] is False

    def test_set_coin_config(self):
        from core.coin_manager import set_coin_config, get_coin_config

        set_coin_config('BTCUSDT', {'sl_pct': 0.05, 'auto_trade': True})
        cfg = get_coin_config('BTCUSDT')
        assert cfg['sl_pct'] == 0.05
        assert cfg['auto_trade'] is True

    def test_remove_coin_clears_config(self):
        from core.coin_manager import add_coin, remove_coin, set_coin_config, get_coin_config

        add_coin('ADAUSDT')
        set_coin_config('ADAUSDT', {'sl_pct': 0.03})
        remove_coin('ADAUSDT')
        cfg = get_coin_config('ADAUSDT')
        assert cfg['sl_pct'] == 0.02  # default restored

    def test_list_coin_configs(self):
        from core.coin_manager import list_coin_configs, set_coin_config

        set_coin_config('BTCUSDT', {'sl_pct': 0.03})
        configs = list_coin_configs()
        btc = [c for c in configs if c['symbol'] == 'BTCUSDT']
        assert btc
        assert btc[0]['sl_pct'] == 0.03


class TestAgentManager:
    def test_agent_manager_modules_importable(self):
        from core import agent_manager  # noqa: F401
        assert True

    def test_agent_manager_has_core_functions(self):
        from core.agent_manager import run_all_cycles, run_single_coin, get_last_cycle, get_all_last_cycles

        assert callable(run_all_cycles)
        assert callable(run_single_coin)
        assert callable(get_last_cycle)
        assert callable(get_all_last_cycles)

    def test_last_cycle_none_on_fresh(self):
        from core.agent_manager import get_last_cycle, get_all_last_cycles

        assert get_last_cycle('BTCUSDT') is None
        assert get_all_last_cycles() == {}

    @pytest.mark.asyncio
    async def test_run_single_coin_timeout_graceful(self):
        """When cycle raises, result is error dict."""
        from unittest.mock import patch, AsyncMock

        from core.coin_manager import set_active_coins
        from core.agent_manager import run_single_coin

        set_active_coins(['BTCUSDT'])

        with patch('core.agent_manager._fetch_closes', return_value=[]):
            with patch('core.agent_desk.run_cycle', side_effect=Exception('agent_crash')):
                result = await run_single_coin('BTCUSDT', mode='demo', timeout=5.0)
                assert 'error' in result
                assert 'symbol' in result
    
    @pytest.mark.asyncio
    async def test_run_all_cycles_uses_mocked_fetch(self):
        from unittest.mock import patch, AsyncMock

        from core.coin_manager import set_active_coins
        from core.agent_manager import run_all_cycles

        set_active_coins(['BTCUSDT'])

        with patch('core.agent_manager._fetch_closes', return_value=[50000.0 + i * 100 for i in range(100)]):
            mock_cycle = {
                'status': 'ok',
                'symbol': 'BTCUSDT',
                'decision': {'verdict': 'buy', 'confidence': 0.7, 'reasoning': 'test'},
            }
            with patch('core.agent_desk.run_cycle', return_value=mock_cycle):
                results = await run_all_cycles(mode='demo', timeout=5.0)
                assert len(results) > 0
                assert results[0]['symbol'] == 'BTCUSDT'
                assert results[0]['status'] == 'ok'
