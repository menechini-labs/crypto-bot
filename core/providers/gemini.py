"""Google Gemini provider — generateContent API."""

import json
import logging
import os
import urllib.error
import urllib.request

from .base import LLMProvider
from .rate_limiter import RateLimiter, RateLimitExceeded
from ..credential_store import CredentialStore

log = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    """Google AI Studio / Vertex AI Gemini API."""

    API_KEY_ENV = 'GEMINI_API_KEY'

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_requests_per_min: int = 10,
        max_tokens_per_min: int = 50000,
    ):
        self._api_key = api_key or self._resolve_key()
        self._model = model or 'gemini-1.5-flash'
        self._rate_limiter = RateLimiter(
            max_requests_per_min=max_requests_per_min,
            max_tokens_per_min=max_tokens_per_min,
        )

    def _resolve_key(self) -> str:
        try:
            store = CredentialStore()
            if store.exists():
                return store.get('gemini_api_key')
        except Exception:
            pass
        return os.getenv(self.API_KEY_ENV, '')

    @property
    def name(self) -> str:
        return 'gemini'

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    def generate(self, prompt: str, *, max_tokens: int = 256, temperature: float = 0.3, model: str | None = None) -> str:
        effective_model = model or self._model
        if not self._api_key:
            raise ValueError(f'{self.name}: API key not configured')

        if not self._rate_limiter.acquire(tokens=max_tokens):
            raise RateLimitExceeded(f'{self.name}: rate limit exceeded')

        url = f'https://generativelanguage.googleapis.com/v1beta/models/{effective_model}:generateContent?key={self._api_key}'
        payload = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': temperature,
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                candidates = data.get('candidates', [])
                if not candidates:
                    return ''
                parts = candidates[0].get('content', {}).get('parts', [])
                text = ' '.join(p.get('text', '') for p in parts)
                return text.strip().lower()
        except urllib.error.HTTPError as e:
            log.exception('Gemini HTTP error %s: %s', e.code, e.read().decode())
            raise
        except Exception:
            log.exception('Gemini request failed')
            raise

    def list_models(self) -> list[str]:
        return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash-exp']

    def health_check(self) -> bool:
        try:
            self.generate('say ok', max_tokens=5)
            return True
        except Exception:
            return False
