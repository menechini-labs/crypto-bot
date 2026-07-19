"""Provider registry."""

from .base import LLMProvider
from .rate_limiter import RateLimiter, RateLimitExceeded
from .openai import OpenAIProvider
from .deepseek import DeepSeekProvider
from .claude import ClaudeProvider
from .gemini import GeminiProvider
from .qwen import QwenProvider
from . import base, openai, deepseek, claude, gemini, qwen

__all__ = [
    'LLMProvider', 'RateLimiter', 'RateLimitExceeded',
    'OpenAIProvider', 'DeepSeekProvider', 'ClaudeProvider',
    'GeminiProvider', 'QwenProvider',
    'base', 'openai', 'deepseek', 'claude', 'gemini', 'qwen',
]

# Auto-registry
_PROVIDER_CLASSES: dict[str, type[LLMProvider]] = {
    'openai': OpenAIProvider,
    'deepseek': DeepSeekProvider,
    'claude': ClaudeProvider,
    'gemini': GeminiProvider,
    'qwen': QwenProvider,
}

def get_provider_class(name: str) -> type[LLMProvider]:
    if name not in _PROVIDER_CLASSES:
        raise ValueError(f'Unknown provider: {name}. Known: {list_providers()}')
    return _PROVIDER_CLASSES[name]

def list_providers() -> list[str]:
    return list(_PROVIDER_CLASSES.keys())
