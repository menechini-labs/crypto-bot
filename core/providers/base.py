"""Abstract base class for all LLM providers."""

from abc import ABC, abstractmethod
from .rate_limiter import RateLimiter

class LLMProvider(ABC):
    """Every LLM provider implements generate(), list_models(), health_check()."""

    @abstractmethod
    def generate(self, prompt: str, *, max_tokens: int = 256, temperature: float = 0.3, model: str | None = None) -> str:
        """Send prompt to LLM, return lowercase response string."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return list of available model names for this provider."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if provider is reachable and API key is valid."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'openai', 'claude')."""
        ...

    @property
    @abstractmethod
    def rate_limiter(self) -> RateLimiter:
        """Per-provider rate limiter instance."""
        ...
