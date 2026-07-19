"""OpenAI-compatible provider (OpenAI, DeepSeek, Qwen share this format)."""

import json
import logging
import os
import urllib.error
import urllib.request

from .base import LLMProvider
from .rate_limiter import RateLimiter
from ..credential_store import CredentialStore

log = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    """Provider for OpenAI-compatible chat completion API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_requests_per_min: int = 10,
        max_tokens_per_min: int = 100000,
    ):
        self._api_key = api_key or self._resolve_key()
        self._base_url = (base_url or os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')).rstrip('/')
        self._model = model or os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
        self._rate_limiter = RateLimiter(
            max_requests_per_min=max_requests_per_min,
            max_tokens_per_min=max_tokens_per_min,
        )

    def _resolve_key(self) -> str:
        # Encrypted store first, then env var
        try:
            store = CredentialStore()
            if store.exists():
                return store.get('llm_api_key')
        except Exception:
            pass
        return os.getenv('LLM_API_KEY', '')

    @property
    def name(self) -> str:
        return 'openai'

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    def generate(self, prompt: str, *, max_tokens: int = 256, temperature: float = 0.3, model: str | None = None) -> str:
        effective_model = model or self._model
        if not self._api_key:
            raise ValueError(f'{self.name}: API key not configured')

        if not self._rate_limiter.acquire(tokens=max_tokens):
            from .rate_limiter import RateLimitExceeded
            raise RateLimitExceeded(f'{self.name}: rate limit exceeded')

        headers = {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': effective_model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        req = urllib.request.Request(
            f'{self._base_url}/chat/completions',
            data=json.dumps(payload).encode(),
            headers=headers,
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode()
                idx = raw.rfind('}')
                if idx > 0:
                    raw = raw[: idx + 1]
                data = json.loads(raw)
                return data['choices'][0]['message']['content'].strip().lower()
        except urllib.error.HTTPError as e:
            log.exception('OpenAI HTTP error %s: %s', e.code, e.read().decode())
            raise
        except Exception:
            log.exception('OpenAI request failed')
            raise

    def list_models(self) -> list[str]:
        return ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o']

    def health_check(self) -> bool:
        try:
            # Quick validation: a minimal chat
            self.generate('say ok', max_tokens=10)
            return True
        except Exception:
            return False
