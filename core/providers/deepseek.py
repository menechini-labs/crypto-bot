"""DeepSeek provider — OpenAI-compatible API."""

from .openai import OpenAIProvider

class DeepSeekProvider(OpenAIProvider):
    """DeepSeek uses same OpenAI-compatible format, different base URL."""

    def __init__(self, api_key: str | None = None, model: str | None = None, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url='https://api.deepseek.com/v1',
            model=model or 'deepseek-chat',
            **kwargs,
        )

    @property
    def name(self) -> str:
        return 'deepseek'

    def list_models(self) -> list[str]:
        return ['deepseek-chat', 'deepseek-reasoner']
