"""Tests for provider interface, registry, rate limiter."""

import json
import os
import time
from unittest.mock import patch, MagicMock
import pytest
from core.providers.base import LLMProvider
from core.providers.rate_limiter import RateLimiter, RateLimitExceeded
from core.providers.openai import OpenAIProvider
from core.providers.deepseek import DeepSeekProvider
from core.providers.claude import ClaudeProvider
from core.providers.gemini import GeminiProvider
from core.providers.qwen import QwenProvider
from core.llm_client import get_provider, list_providers, chat

# --- Rate limiter ---

class TestRateLimiter:
    def test_acquire_allows_within_limit(self):
        rl = RateLimiter(max_requests_per_min=5, max_tokens_per_min=100000)
        for _ in range(5):
            assert rl.acquire() is True

    def test_acquire_blocks_when_exceeded(self):
        rl = RateLimiter(max_requests_per_min=2, max_tokens_per_min=100000)
        assert rl.acquire() is True
        assert rl.acquire() is True
        assert rl.acquire(wait_ms=50) is False  # throttle

    def test_token_budget_respected(self):
        rl = RateLimiter(max_requests_per_min=10, max_tokens_per_min=100)
        assert rl.acquire(tokens=60) is True
        assert rl.acquire(tokens=60, wait_ms=50) is False  # 120 > 100

    def test_prune_removes_old_entries(self):
        rl = RateLimiter(max_requests_per_min=1, max_tokens_per_min=100000)
        rl._window = [(time.monotonic() - 120, 0)]  # 2 minutes ago
        rl._prune()
        assert len(rl._window) == 0

    def test_record_tokens(self):
        rl = RateLimiter(max_requests_per_min=10, max_tokens_per_min=1000)
        rl.record_tokens(500)
        rl.record_tokens(500)
        assert len(rl._window) == 2
        rl.record_tokens(500)  # over budget, logged
        assert len(rl._window) == 2  # not appended

# --- Providers ---

class TestOpenAIProvider:
    def test_name(self):
        assert OpenAIProvider().name == 'openai'

    def test_resolve_key_from_env(self):
        with patch.dict(os.environ, {'LLM_API_KEY': 'test-key-123'}):
            p = OpenAIProvider(api_key=None)
            assert p._api_key == 'test-key-123'

    def test_generate_http_error_raises(self):
        p = OpenAIProvider(api_key='dummy')
        with pytest.raises(Exception):
            p.generate('test')

    def test_list_models(self):
        models = OpenAIProvider().list_models()
        assert 'gpt-4' in models

class TestDeepSeekProvider:
    def test_name(self):
        assert DeepSeekProvider().name == 'deepseek'

    def test_default_model(self):
        assert DeepSeekProvider()._model == 'deepseek-chat'

    def test_list_models(self):
        models = DeepSeekProvider().list_models()
        assert 'deepseek-chat' in models

class TestClaudeProvider:
    def test_name(self):
        assert ClaudeProvider().name == 'claude'

    def test_resolve_key_env(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-test'}):
            p = ClaudeProvider(api_key=None)
            assert p._api_key == 'sk-ant-test'

    def test_list_models(self):
        models = ClaudeProvider().list_models()
        assert 'claude-3-haiku-20240307' in models

class TestGeminiProvider:
    def test_name(self):
        assert GeminiProvider().name == 'gemini'

    def test_resolve_key_env(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'ai-test-key'}):
            p = GeminiProvider(api_key=None)
            assert p._api_key == 'ai-test-key'

    def test_list_models(self):
        models = GeminiProvider().list_models()
        assert 'gemini-1.5-flash' in models

class TestQwenProvider:
    def test_name(self):
        assert QwenProvider().name == 'qwen'

    def test_list_models(self):
        models = QwenProvider().list_models()
        assert 'qwen-turbo' in models

class TestRegistry:
    def test_list_providers(self):
        names = list_providers()
        assert 'openai' in names
        assert 'claude' in names
        assert len(names) == 5

    def test_get_provider(self):
        p = get_provider('openai')
        assert p.name == 'openai'

    def test_get_unknown_provider(self):
        with pytest.raises(ValueError, match='Unknown provider'):
            get_provider('nonexistent')

    def test_provider_implements_abstract(self):
        for name in list_providers():
            p = get_provider(name, api_key='test')
            assert hasattr(p, 'generate')
            assert hasattr(p, 'list_models')
            assert hasattr(p, 'health_check')
            assert hasattr(p, 'rate_limiter')

class TestLLMClientCompat:
    def test_is_enabled_false(self):
        with patch.dict(os.environ, {'ENABLE_LLM': '0'}):
            from core.llm_client import is_enabled
            assert is_enabled() is False

    def test_chat_raises_when_disabled(self):
        with patch.dict(os.environ, {'ENABLE_LLM': '0'}):
            from core.llm_client import chat
            with pytest.raises(RuntimeError, match='LLM disabled'):
                chat('test')


class TestHotSwap:
    def test_get_active_provider_config_default(self):
        from core.llm_client import get_active_provider_config, _ACTIVE_INIT_DONE
        _ACTIVE_INIT_DONE = False  # reset for test
        cfg = get_active_provider_config()
        assert 'active_provider' in cfg
        assert 'fallback_order' in cfg
        assert 'available_providers' in cfg
        assert cfg['active_provider'] in cfg['available_providers']

    def test_set_active_provider_invalid_raises(self):
        from core.llm_client import set_active_provider, _ACTIVE_INIT_DONE
        _ACTIVE_INIT_DONE = False
        with pytest.raises(ValueError, match='Unknown provider'):
            set_active_provider('nonexistent')

    def test_set_active_provider_valid(self):
        from core.llm_client import (
            set_active_provider, get_active_provider_config, _ACTIVE_INIT_DONE
        )
        _ACTIVE_INIT_DONE = False
        set_active_provider('deepseek')
        cfg = get_active_provider_config()
        assert cfg['active_provider'] == 'deepseek'

    def test_set_active_provider_clears_cache(self):
        from core.llm_client import (
            set_active_provider, get_provider, _ACTIVE_INIT_DONE,
            _PROVIDER_INSTANCES
        )
        _ACTIVE_INIT_DONE = False
        _PROVIDER_INSTANCES.clear()
        _ = get_provider('openai')
        assert 'openai' in _PROVIDER_INSTANCES
        set_active_provider('deepseek')
        assert 'openai' not in _PROVIDER_INSTANCES  # cache cleared

    def test_set_active_provider_with_fallback(self):
        from core.llm_client import (
            set_active_provider, get_active_provider_config, _ACTIVE_INIT_DONE
        )
        _ACTIVE_INIT_DONE = False
        set_active_provider('qwen', fallback_order=['qwen', 'openai'])
        cfg = get_active_provider_config()
        assert cfg['active_provider'] == 'qwen'
        assert cfg['fallback_order'] == ['qwen', 'openai']

    def test_set_active_provider_invalid_fallback_raises(self):
        from core.llm_client import set_active_provider, _ACTIVE_INIT_DONE
        _ACTIVE_INIT_DONE = False
        with pytest.raises(ValueError, match='Unknown provider'):
            set_active_provider('openai', fallback_order=['bogus'])
