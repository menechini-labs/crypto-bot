"""Stdlib-only LLM client (OpenAI-compatible chat completions).

Reused by LLMStrategy and AgentDesk LLMDecisionCore.
Config via env: LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, ENABLE_LLM.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from core.credential_store import CredentialStore
from core.providers import get_provider_class, list_providers as _list_providers, LLMProvider

log = logging.getLogger(__name__)

# Provider registry wrapper
_PROVIDER_INSTANCES: dict[str, LLMProvider] = {}

def register_provider(name: str, instance: LLMProvider):
    _PROVIDER_INSTANCES[name] = instance

def get_provider(name: str, **kwargs) -> LLMProvider:
    if name not in _PROVIDER_INSTANCES:
        cls = get_provider_class(name)
        instance = cls(**kwargs)
        _PROVIDER_INSTANCES[name] = instance
    return _PROVIDER_INSTANCES[name]

def list_providers() -> list[str]:
    return _list_providers()

# --- Runtime provider config (hot-swap) ---
_ACTIVE_PROVIDER: str = ''
_ACTIVE_FALLBACK_ORDER: list[str] = []
_ACTIVE_INIT_DONE: bool = False

def _init_active_provider():
    global _ACTIVE_PROVIDER, _ACTIVE_FALLBACK_ORDER, _ACTIVE_INIT_DONE
    if _ACTIVE_INIT_DONE:
        return
    fallback_str = os.getenv('LLM_FALLBACK_ORDER', 'openai')
    _ACTIVE_FALLBACK_ORDER = [n.strip() for n in fallback_str.split(',') if n.strip()]
    _ACTIVE_PROVIDER = os.getenv('LLM_ACTIVE_PROVIDER', _ACTIVE_FALLBACK_ORDER[0] if _ACTIVE_FALLBACK_ORDER else 'openai')
    _ACTIVE_INIT_DONE = True

def set_active_provider(provider: str, fallback_order: list[str] | None = None) -> None:
    """Switch active provider at runtime. Clears cached instances."""
    global _ACTIVE_PROVIDER, _ACTIVE_FALLBACK_ORDER
    _init_active_provider()
    if provider not in list_providers():
        raise ValueError(f'Unknown provider: {provider}')
    if fallback_order is not None:
        for name in fallback_order:
            if name not in list_providers():
                raise ValueError(f'Unknown provider in fallback: {name}')
        _ACTIVE_FALLBACK_ORDER = list(fallback_order)
    _ACTIVE_PROVIDER = provider
    _PROVIDER_INSTANCES.clear()
    log.info('Active provider set to %s (fallback: %s)', provider, _ACTIVE_FALLBACK_ORDER)

def get_active_provider_config() -> dict:
    """Return current provider configuration for status endpoints."""
    _init_active_provider()
    return {
        'active_provider': _ACTIVE_PROVIDER,
        'fallback_order': list(_ACTIVE_FALLBACK_ORDER),
        'available_providers': list_providers(),
    }

# Lazy-initialized credential store
_llm_cred_store: CredentialStore | None = None


def _get_llm_cred_store() -> CredentialStore:
    global _llm_cred_store
    if _llm_cred_store is None:
        _llm_cred_store = CredentialStore()
    return _llm_cred_store


def _load_dotenv(path: str | None = None) -> None:
    """Minimal .env loader - reads KEY=VAL lines, sets os.environ if not already set."""
    if path is None:
        # try common locations
        for candidate in ('.env', os.path.join(os.path.dirname(__file__), '..', '.env')):
            if os.path.isfile(candidate):
                path = candidate
                break
        else:
            return  # no .env found
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, _, val = line.partition('=')
                key = key.strip()
                val = val.strip()
                if key and not os.environ.get(key):
                    os.environ[key] = val
    except Exception:
        pass


def is_enabled() -> bool:
    _load_dotenv()
    return os.getenv('ENABLE_LLM', '0') == '1'


def api_key() -> str:
    _load_dotenv()
    # Try encrypted store first, fall back to env var for backward compat
    try:
        store = _get_llm_cred_store()
        if store.exists():
            return store.get('llm_api_key')
    except Exception:
        pass
    return os.getenv('LLM_API_KEY', '')


def base_url() -> str:
    _load_dotenv()
    return os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')


def model() -> str:
    _load_dotenv()
    return os.getenv('LLM_MODEL', 'gpt-3.5-turbo')


def chat(prompt: str, max_tokens: int = 256, temperature: float = 0.3) -> str:
    """POST prompt to LLM using active provider with fallback chain."""
    if not is_enabled():
        raise RuntimeError('LLM disabled (ENABLE_LLM=0)')
    _init_active_provider()

    last_error: Exception | None = None
    for name in _ACTIVE_FALLBACK_ORDER:
        try:
            provider = get_provider(name)
            response = provider.generate(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if len(_ACTIVE_FALLBACK_ORDER) > 1:
                log.info('Used provider: %s (fallback chain: %s)', name, _ACTIVE_FALLBACK_ORDER)
            return response
        except Exception as e:
            log.warning('Provider %s failed: %s', name, e)
            last_error = e

    raise last_error or RuntimeError('no LLM providers available')
