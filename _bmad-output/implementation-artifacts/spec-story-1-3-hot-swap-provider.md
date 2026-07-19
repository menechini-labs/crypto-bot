---
title: 'Story 1.3 — Hot-Swap Provider Mid-Strategy'
type: 'feature'
created: '2026-07-19'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: e7b1716
context:
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
  - '_bmad-output/implementation-artifacts/spec-story-1-2-unified-llm-provider-interface.md'
  - '_bmad-output/planning-artifacts/epics.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** User must restart server to switch LLM provider or fallback chain. No runtime endpoint exists to change provider config. PipelineView has no visibility into which provider is active.

**Approach:**
1. Add `_ACTIVE_PROVIDER` and `_ACTIVE_FALLBACK_ORDER` to `core/llm_client.py` — runtime mutable state
2. `set_active_provider(name)` — switch active provider at runtime, clear cached provider instances that differ
3. `get_active_provider_config()` — returns current config for status
4. Refactor `chat()` to use `_ACTIVE_PROVIDER` and `_ACTIVE_FALLBACK_ORDER` instead of always reading env var
5. Endpoints: `GET /api/config/provider` → current provider + fallback chain + available providers
6. Endpoints: `POST /api/config/provider` → switch provider
7. Update `GET /api/health` to include `active_provider`
8. In-flight safety: `chat()` uses a lock-aware approach — switch takes effect on next call, not mid-request

## Boundaries & Constraints

**Always:**
- `_ACTIVE_PROVIDER` starts from env var `LLM_ACTIVE_PROVIDER` or `LLM_FALLBACK_ORDER` (first entry) on init
- `_ACTIVE_FALLBACK_ORDER` starts from `LLM_FALLBACK_ORDER` env var
- `set_active_provider()` clears cached instances for providers that are no longer first in chain (forces fresh on next call with current env)
- Switch is atomic: next `chat()` call uses new provider
- All existing callers unchanged — `chat()`, `is_enabled()`, `api_key()` etc.

**Block If:**
- `_PROVIDER_INSTANCES` cache eviction removes a provider that is mid-request — but `chat()` is synchronous, so no concurrency issue for single-threaded calls

**Never:**
- No new external deps
- No persistence of provider choice across restart (env var is source of truth)
- No UI changes in this story (PipelineView update is optional/future)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| GET provider config | — | returns active_provider + fallback_order + available list | N/A |
| POST switch to valid provider | {"provider": "claude"} | 200 + provider switched + log | ValueError → 400 |
| POST switch to unknown provider | {"provider": "bogus"} | 400 "unknown provider" | N/A |
| POST switch with fallback chain | {"provider": "claude", "fallback_order": "claude,openai"} | 200 + both updated | N/A |
| chat() after switch | provider="deepseek" | uses DeepSeek provider | N/A |
| chat() with fallback + first fails | fallback=[deepseek, openai], deepseek down | openai used | N/A |
| Provider change during fallback | switch while fallback in progress | next call uses new order | N/A |

</intent-contract>

## Code Map

- `core/llm_client.py` — MODIFY: add `_ACTIVE_PROVIDER`, `_ACTIVE_FALLBACK_ORDER`, `set_active_provider()`, `get_active_provider_config()`, refactor `chat()`
- `core/strategy_api.py` — MODIFY: add `GET /api/config/provider`, `POST /api/config/provider`
- `tests/unit/test_providers.py` — ADD tests for hot-swap functions

## Design Notes

**`llm_client.py` changes:**

```python
# --- Runtime provider config ---
import copy

_ACTIVE_PROVIDER: str = ''
_ACTIVE_FALLBACK_ORDER: list[str] = []

def _init_active_provider():
    """Initialize from env vars. Called once lazily."""
    global _ACTIVE_PROVIDER, _ACTIVE_FALLBACK_ORDER
    if _ACTIVE_PROVIDER:
        return
    fallback_str = os.getenv('LLM_FALLBACK_ORDER', 'openai')
    _ACTIVE_FALLBACK_ORDER = [n.strip() for n in fallback_str.split(',') if n.strip()]
    _ACTIVE_PROVIDER = os.getenv('LLM_ACTIVE_PROVIDER', _ACTIVE_FALLBACK_ORDER[0] if _ACTIVE_FALLBACK_ORDER else 'openai')

def set_active_provider(provider: str, fallback_order: list[str] | None = None) -> None:
    """Switch active provider at runtime. clears cached instances."""
    _init_active_provider()
    if provider not in list_providers():
        raise ValueError(f'Unknown provider: {provider}')
    if fallback_order is not None:
        for name in fallback_order:
            if name not in list_providers():
                raise ValueError(f'Unknown provider in fallback: {name}')
        _ACTIVE_FALLBACK_ORDER = fallback_order
    _ACTIVE_PROVIDER = provider
    # Clear cached instances so next call gets fresh provider with current env state
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
```

**Refactored `chat()`:**

```python
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
```

**Health update** — add to `/api/health` response:
```python
'llm_active_provider': get_active_provider_config().get('active_provider'),
'llm_fallback_order': get_active_provider_config().get('fallback_order'),
'llm_available_providers': get_active_provider_config().get('available_providers'),
```

## Tasks & Acceptance

- [ ] `core/llm_client.py` — add `_init_active_provider()`, `set_active_provider()`, `get_active_provider_config()`, refactor `chat()` to use new globals
- [ ] `core/strategy_api.py` — add `GET /api/config/provider`, `POST /api/config/provider`
- [ ] `core/strategy_api.py` — update `/api/health` with LLM provider info
- [ ] `tests/unit/test_providers.py` — add tests for `set_active_provider()`, `get_active_provider_config()`, invalid provider

**Acceptance Criteria:**
- Given POST /api/config/provider {"provider": "deepseek"}, when called, then subsequent chat() uses DeepSeek
- Given POST /api/config/provider {"provider": "bogus"}, when called, then 400 error
- Given GET /api/config/provider, when called, then returns active_provider, fallback_order, available_providers
- Given /api/health, when called, then includes llm_active_provider and llm_fallback_order
- Given switch happens, when next chat() call occurs, then old provider instances are cleared

## Spec Change Log

<!-- Empty until first review loopback -->
