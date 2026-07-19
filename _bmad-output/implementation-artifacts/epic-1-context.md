# Epic 1 Context: Fundação Segura de Múltiplos Providers

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

User can configure multiple LLM providers with encrypted credentials and hot-swap them mid-strategy without restart. Eliminates current monolithic switch-case provider pattern, protects secrets at rest via AES-GCM, enables runtime provider switching for cost/latency/quality trade-offs.

## Stories

- Story 1.1 Encrypted Credential Store — DONE
- Story 1.2 Unified LLM Provider Interface — CURRENT
- Story 1.3 Hot-Swap Provider Mid-Strategy

## Requirements & Constraints

- Replace current `llm_client.py` switch-case with abstract base class + pluggable provider registry (initial: OpenAI, DeepSeek, Claude, Gemini, Qwen)
- Each provider: self-contained class implementing common interface; adding new provider = zero pipeline changes
- Provider registry auto-discovers and loads providers dynamically
- Per-model rate limits (tokens/min, requests/min) with queue/defer when budget exceeded
- Fallback chains: on provider failure, system automatically tries next provider in chain; fallback reason + latency per provider logged
- All existing tests pass; backward compatibility with existing strategies maintained during migration
- Python-native only; no Go deps; OpenClaw-native unchanged
- Integration point: `config_loader.py` (existing YAML config system)

## Technical Decisions

- Abstract base class `LLMProvider` defining `generate()`, `list_models()`, `health_check()`
- Provider registry: loads all classes from known module path, keyed by provider name; pipeline selects by name
- Rate limiting: each provider instance tracks token/request budgets with configurable limits; incoming requests queue if budget exhausted
- Existing `core/llm_client.py` refactored: current OpenAI logic extracted into `OpenAIProvider`; other providers added as classes
- Existing `StrategyBase.generate_trade_signal()` calls provider interface; no orchestration changes needed
- Migration path: old `llm_client.py` functions deprecated one release before removal; new code uses provider interface

## Cross-Story Dependencies

- Story 1.2 depends on Story 1.1 (Credential Store) — provider constructors get API keys from encrypted store
- Story 1.3 depends on Story 1.2 — runtime switching requires unified interface
- No cross-epic deps
