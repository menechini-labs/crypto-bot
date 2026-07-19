"""Qwen provider — DashScope OpenAI-compatible API."""

from .openai import OpenAIProvider

class QwenProvider(OpenAIProvider):
    """Alibaba Qwen via DashScope (OpenAI-compatible)."""

    def __init__(self, api_key: str | None = None, model: str | None = None, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            model=model or 'qwen-turbo',
            **kwargs,
        )

    @property
    def name(self) -> str:
        return 'qwen'

    def list_models(self) -> list[str]:
        return ['qwen-turbo', 'qwen-plus', 'qwen-max']
