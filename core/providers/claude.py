"""Anthropic Claude provider — Messages API."""

import json
import logging
import os
import urllib.error
import urllib.request

from .base import LLMProvider
from .rate_limiter import RateLimiter, RateLimitExceeded
from ..credential_store import CredentialStore

log = logging.getLogger(__name__)

class ClaudeProvider(LLMProvider):
    """Anthropic Messages API (POST /v1/messages)."""

    API_KEY_ENV = 'ANTHROPIC_API_KEY'

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_requests_per_min: int = 5,
        max_tokens_per_min: int = 50000,
    ):
        self._api_key = api_key or self._resolve_key()
        self._model = model or 'claude-3-haiku-20240307'
        self._rate_limiter = RateLimiter(
            max_requests_per_min=max_requests_per_min,
            max_tokens_per_min=max_tokens_per_min,
        )

    def _resolve_key(self) -> str:
        try:
            store = CredentialStore()
            if store.exists():
                return store.get('anthropic_api_key')
        except Exception:
            pass
        return os.getenv(self.API_KEY_ENV, '')

    @property
    def name(self) -> str:
        return 'claude'

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    def generate(self, prompt: str, *, max_tokens: int = 256, temperature: float = 0.3, model: str | None = None) -> str:
        effective_model = model or self._model
        if not self._api_key:
            raise ValueError(f'{self.name}: API key not configured')

        if not self._rate_limiter.acquire(tokens=max_tokens):
            raise RateLimitExceeded(f'{self.name}: rate limit exceeded')

        headers = {
            'x-api-key': self._api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': effective_model,
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        if temperature != 0.3:
            payload['temperature'] = temperature

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=json.dumps(payload).encode(),
            headers=headers,
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                content_blocks = data.get('content', [])
                text = ' '.join(b.get('text', '') for b in content_blocks if b.get('type') == 'text')
                return text.strip().lower()
        except urllib.error.HTTPError as e:
            log.exception('Claude HTTP error %s: %s', e.code, e.read().decode())
            raise
        except Exception:
            log.exception('Claude request failed')
            raise

    def list_models(self) -> list[str]:
        return ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229', 'claude-3-5-sonnet-20241022']

    def health_check(self) -> bool:
        try:
            self.generate('say ok', max_tokens=5)
            return True
        except Exception:
            return False
