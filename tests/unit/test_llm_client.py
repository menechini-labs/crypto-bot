"""Tests for core.llm_client: registry, backward-compat, and hot-swap (stories 1.2 / 1.3)."""

from __future__ import annotations

import importlib

import pytest

import core.llm_client as llm_client
from core.providers import list_providers as registry_list_providers


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Reset llm_client runtime state between tests."""
    importlib.reload(llm_client)
    monkeypatch.setenv('ENABLE_LLM', '1')
    monkeypatch.setenv('LLM_FALLBACK_ORDER', 'openai')
    monkeypatch.setenv('LLM_ACTIVE_PROVIDER', 'openai')
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    # Re-trigger init by clearing done flag
    llm_client._ACTIVE_INIT_DONE = False
    llm_client._ACTIVE_PROVIDER = ''
    llm_client._ACTIVE_FALLBACK_ORDER = []
    llm_client._PROVIDER_INSTANCES.clear()
    yield
    importlib.reload(llm_client)


# --- Registry / provider resolution (story 1.2) ---

def test_list_providers_returns_all_five():
    assert llm_client.list_providers() == ['openai', 'deepseek', 'claude', 'gemini', 'qwen']


def test_registry_matches_provider_module():
    assert llm_client.list_providers() == registry_list_providers()


def test_get_provider_unknown_raises_valueerror():
    with pytest.raises(ValueError):
        llm_client.get_provider_class('bogus')


def test_get_provider_returns_instance_and_caches():
    p1 = llm_client.get_provider('openai')
    p2 = llm_client.get_provider('openai')
    assert p1 is p2  # cached


# --- Backward-compat API (story 1.2) ---

def test_is_enabled_true_when_env_set(monkeypatch):
    monkeypatch.setenv('ENABLE_LLM', '1')
    assert llm_client.is_enabled() is True


def test_is_enabled_false_when_env_unset(monkeypatch):
    monkeypatch.delenv('ENABLE_LLM', raising=False)
    # Prevent .env on disk from repopulating the var
    monkeypatch.setattr(llm_client, '_load_dotenv', lambda *a, **k: None)
    assert llm_client.is_enabled() is False


def test_chat_raises_when_disabled(monkeypatch):
    monkeypatch.setenv('ENABLE_LLM', '0')
    with pytest.raises(RuntimeError):
        llm_client.chat('hello')


def test_api_key_base_url_model_defaults(monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_MODEL', raising=False)
    # Prevent .env on disk from repopulating the vars
    monkeypatch.setattr(llm_client, '_load_dotenv', lambda *a, **k: None)
    assert llm_client.base_url() == 'https://api.openai.com/v1'
    assert llm_client.model() == 'gpt-3.5-turbo'
    # api_key falls back to empty env when store has no key
    assert llm_client.api_key() == ''


# --- Hot-swap (story 1.3) ---

def test_active_provider_config_initialized_from_env():
    cfg = llm_client.get_active_provider_config()
    assert cfg['active_provider'] == 'openai'
    assert cfg['fallback_order'] == ['openai']
    assert set(cfg['available_providers']) == {
        'openai', 'deepseek', 'claude', 'gemini', 'qwen'
    }


def test_set_active_provider_valid():
    llm_client.set_active_provider('claude')
    cfg = llm_client.get_active_provider_config()
    assert cfg['active_provider'] == 'claude'
    # cached instances cleared so next call rebuilds
    assert llm_client._PROVIDER_INSTANCES == {}


def test_set_active_provider_with_fallback_order():
    llm_client.set_active_provider('claude', fallback_order=['claude', 'openai'])
    cfg = llm_client.get_active_provider_config()
    assert cfg['active_provider'] == 'claude'
    assert cfg['fallback_order'] == ['claude', 'openai']


def test_set_active_provider_unknown_raises_valueerror():
    with pytest.raises(ValueError):
        llm_client.set_active_provider('bogus')


def test_set_active_provider_unknown_in_fallback_raises_valueerror():
    with pytest.raises(ValueError):
        llm_client.set_active_provider('openai', fallback_order=['openai', 'bogus'])
