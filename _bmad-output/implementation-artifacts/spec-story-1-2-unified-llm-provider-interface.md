---
title: 'Story 1.2 — Unified LLM Provider Interface'
type: 'feature'
created: '2026-07-19'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 358831d
context:
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
  - '_bmad-output/planning-artifacts/epics.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `llm_client.py` monolithic — single HTTP client, hardcoded to OpenAI-compatible endpoint. No pluggable provider, no fallback, no rate limits. Adding DeepSeek/Claude/Gemini/Qwen means either switch-case or separate clients. `llm_strategy.py` duplicates `_api_key()` logic. `agent_desk.py` calls `llm_client.chat()` directly.

**Approach:**
1. Abstract base class `LLMProvider` in `core/providers/base.py` — `generate()`, `list_models()`, `health_check()`, `rate_limiter`, `model_name`
2. Provider classes: `OpenAIProvider`, `DeepSeekProvider`, `ClaudeProvider`, `GeminiProvider`, `QwenProvider` in `core/providers/`
3. Provider registry in `core/llm_client.py` — `register`, `get_provider`, `list_providers`
4. Refactor `core/llm_client.chat()` to delegate via registry
5. Per-provider rate limits (requests/min, tokens/min)
6. Fallback chain support: [openai, deepseek, claude] → try order, break on success
7. Caller visible functions: `chat()`, `is_enabled()` keep same signature (backward compat)

## Boundaries & Constraints

**Always:**
- Python stdlib + `cryptography` + `httpx` or `urllib` only — no heavy deps
- Each provider class in own file under `core/providers/`
- Rate limit: per-provider configurable via `config_loader` (defaults in code)
- Fallback chain: configurable via `LLM_FALLBACK_ORDER` env var (comma-separated names)
- `_llm_strategy.py` `_api_key()` → refactor to use `CredentialStore.get()` directly (done in Story 1.1)
- `llm_client.api_key()`, `llm_client.base_url()`, `llm_client.model()` → deprecated but kept for one release
- All existing callers (`chat()`, `is_enabled()` in agent_desk.py, llm_strategy.py) continue working unchanged
- 207+ tests pass

**Block If:**
- Extracting existing OpenAI logic into `OpenAIProvider` breaks headers/auth — ensure `Authorization: Bearer` with `LLM_API_KEY` is preserved identically

**Never:**
- No Go, no subprocess, no external services
- No persistence of rate limit state across restarts (simple memory-budget is fine)
- No x402 payments in this story

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal chat via OpenAI provider | prompt, model="gpt-4" | returns lowercase response string | HTTPError → log + raise |
| Provider not in registry | name="bogus" | raises ValueError "unknown provider" | N/A |
| Fallback chain: first fails, second succeeds | openai down, deepseek up | deepseek response returned, log "fallback openai -> deepseek" | Retry logic, silence first error after fallback works |
| All providers in chain fail | all down | original error from first provider raised | Log each failure |
| Rate limit exceeded (requests/min) | burst of 10+ calls | calls queued/rate-limited, log "rate limit: waiting" | Queue with timeout; if timeout exceeded, raise RateLimitError |
| Provider returns non-JSON | garbage response body | raise ProviderError "invalid response" | N/A |
| Provider returns error JSON with choices | valid choices[0] | parse content normally | N/A |
| LLM disabled | ENABLE_LLM=0 | chat() raises RuntimeError("LLM disabled") | Same as before |
| list_models() on a provider | provider name | returns list of model strings | Log error, return empty list |
| health_check() | provider name | returns True if healthy | Returns False, never raise |

</intent-contract>

## Code Map

- `core/providers/__init__.py` — NEW: exports all providers + base
- `core/providers/base.py` — NEW: `LLMProvider` abstract base class
- `core/providers/openai.py` — NEW: `OpenAIProvider`
- `core/providers/deepseek.py` — NEW: `DeepSeekProvider`
- `core/providers/claude.py` — NEW: `ClaudeProvider`
- `core/providers/gemini.py` — NEW: `GeminiProvider`
- `core/providers/qwen.py` — NEW: `QwenProvider`
- `core/providers/rate_limiter.py` — NEW: token/request budget tracker
- `core/llm_client.py` — MODIFY: add provider registry, refactor `chat()`, keep backward compat functions (`api_key()`, `base_url()`, `model()`, `is_enabled()`, `_load_dotenv()`)
- `core/strategy_registry/llm_strategy.py` — MODIFY: refactor `_api_key()` to use `CredentialStore` properly (no change needed — already done in Story 1.1)
- `core/agent_desk.py` — NO CHANGE expected (uses `llm_client.chat()`, `llm_client.is_enabled()`)
- `tests/unit/test_providers.py` — NEW: tests for base, registry, rate limiter
- `tests/unit/test_llm_client.py` — NEW: backward compat + registry integration tests

## Tasks & Acceptance

**Execution:**
- [ ] `core/providers/base.py` — create abstract `LLMProvider` with `generate()`, `list_models()`, `health_check()`, `rate_limiter` property
- [ ] `core/providers/rate_limiter.py` — create `RateLimiter` class tracking requests/min and tokens/min with configurable budgets
- [ ] `core/providers/openai.py` — extract current `chat()` logic into `OpenAIProvider` using stdlib `urllib`
- [ ] `core/providers/deepseek.py` — `DeepSeekProvider` (same OpenAI-compatible API, different base URL + model)
- [ ] `core/providers/claude.py` — `ClaudeProvider` (Anthropic Messages API format: POST /v1/messages, different request body)
- [ ] `core/providers/gemini.py` — `GeminiProvider` (Google AI API: POST /v1beta/models/{model}:generateContent)
- [ ] `core/providers/qwen.py` — `QwenProvider` (Alibaba DashScope, OpenAI-compatible)
- [ ] `core/providers/__init__.py` — export all providers
- [ ] `core/llm_client.py` — add registry (`_PROVIDERS` dict, `register()`, `get_provider()`, `list_providers()`), refactor `chat()` to use registry with fallback chain, keep backward compat functions
- [ ] `tests/unit/test_providers.py` — 10+ tests covering abstract base, registry, rate limiter, each provider parse, edge cases
- [ ] `tests/unit/test_llm_client.py` — 5+ tests covering backward compat, fallback chain, disabled state

**Acceptance Criteria:**
- Given ENABLE_LLM=1 with OpenAI API key, when `chat("test")` is called, then response is returned (same as before)
- Given LLM_FALLBACK_ORDER="deepseek,openai", when DeepSeek is unavailable and OpenAI responds, then OpenAI response is returned and fallback is logged
- Given rate limit is 3 req/min, when 5 calls arrive within the same minute, then 4th and 5th calls are delayed or raise RateLimitError
- Given get_provider("claude"), when called, then a ClaudeProvider instance is returned
- Given all providers are registered, when list_providers() is called, then [openai, deepseek, claude, gemini, qwen] is returned

## Spec Change Log

<!-- Empty until first review loopback -->

## Review Triage Log

<!-- Empty until first review pass -->

## Design Notes

**Provider interface:**
```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, *, max_tokens: int = 256, temperature: float = 0.3, model: str | None = None) -> str: ...
    @abstractmethod
    def list_models(self) -> list[str]: ...
    @abstractmethod
    def health_check(self) -> bool: ...
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def rate_limiter(self) -> 'RateLimiter': ...
```

**Registry pattern:**
```python
_PROVIDERS: dict[str, type[LLMProvider]] = {}

def register(provider_cls: type[LLMProvider]): ...
def get_provider(name: str, api_key: str | None = None, **kwargs) -> LLMProvider: ...
def list_providers() -> list[str]: ...
```

**Rate limiter:**
```python
class RateLimiter:
    def __init__(self, max_requests_per_min: int = 10, max_tokens_per_min: int = 100000): ...
    def acquire(self) -> bool: ...  # blocking poll, returns True if allowed
    def record_tokens(self, count: int): ...
```

**Fallback chain in llm_client.chat():**
```python
def chat(prompt: str, max_tokens: int = 256, temperature: float = 0.3) -> str:
    fallback_order = os.getenv('LLM_FALLBACK_ORDER', 'openai').split(',')
    last_error = None
    for name in fallback_order:
        try:
            provider = get_provider(name.strip())
            return provider.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        except Exception as e:
            log.warning('fallback from %s: %s', name, e)
            last_error = e
    raise last_error or RuntimeError('no LLM providers available')
```

**Provider URL mapping:**
- OpenAI: `base_url() + /chat/completions` (existing)
- DeepSeek: `https://api.deepseek.com/v1/chat/completions` (OpenAI-compatible)
- Claude: `https://api.anthropic.com/v1/messages` (Anthropic Messages API)
- Gemini: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Qwen: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` (OpenAI-compatible)

## Verification

**Commands:**
- `cd /home/node/.openclaw/workspace/crypto-bot && uv run python -m pytest tests/unit/test_providers.py tests/unit/test_llm_client.py -v` — expected: 15+ passed
- `cd /home/node/.openclaw/workspace/crypto-bot && uv run python -m pytest -x --tb=short` — expected: 207+ passed (no regressions)
- `cd /home/node/.openclaw/workspace/crypto-bot && uv run python -c "from core.llm_client import list_providers, get_provider; assert 'openai' in list_providers(); p = get_provider('openai'); print(f'OK: {p.name}')"` — expected: `OK: openai`

**Manual checks:**
- Verify `llm_client.chat("hello")` returns expected output with ENABLE_LLM=1
- Verify `llm_client.chat("hello")` raises RuntimeError with ENABLE_LLM=0
- Verify `list_providers()` returns all 5 providers
