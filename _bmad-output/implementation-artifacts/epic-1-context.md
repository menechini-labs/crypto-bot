# Epic 1 Context: Fundação Segura de Múltiplos Providers
<!-- Generated from planning artifacts. Regenerate via compile-epic-context if planning docs change. -->

## Goal

User can configure multiple LLM providers with encrypted credentials and hot-swap them mid-strategy without restart. This eliminates the current monolithic switch-case provider pattern, adds disk-level secret protection via AES-GCM, and enables runtime provider switching for cost/latency/quality trade-offs — the foundational layer for all multi-provider capabilities.

## Stories

- Story 1.1: Encrypted Credential Store
- Story 1.2: Unified LLM Provider Interface
- Story 1.3: Hot-Swap Provider Mid-Strategy

## Requirements & Constraints

- Replace current `llm_client.py` switch-case with abstract base class + pluggable provider registry (initially: OpenAI, DeepSeek, Claude, Gemini, Qwen)
- Each provider must be a self-contained class implementing the common interface; adding a new provider requires zero changes to pipeline code
- Provider registry must auto-discover and load providers dynamically
- Must support per-model rate limits (tokens/min, requests/min) with queue/defer when budget exceeded
- Fallback chains: on provider failure (network error, rate limit, auth failure), system automatically tries next provider in chain; fallback reason and latency per provider must be logged
- All credentials encrypted at rest using AES-GCM via Python's `cryptography` library; plaintext never written to disk
- Decrypted credentials available only in-memory for session lifetime; session key derived from user-provided passphrase or key material
- Key rotation mechanism must be supported
- Must stay Python-native; no Go dependencies
- Must remain OpenClaw-native (agent runtime architecture unchanged)
- All existing tests (191 passing) must continue passing; backward compatibility with existing strategies must be maintained during migration
- Integration point: `config_loader.py` (existing YAML-based config system)
- CLI or env var for initial credential provisioning; plaintext key never written to disk

## Technical Decisions

- Current state: `llm_client.py` uses stdlib `urllib` with `ENABLE_LLM=1` + `LLM_API_KEY` env var — a single monolithic file with provider-specific branches
- Target: abstract base class (`LLMProvider` or similar) defining `generate()`, `list_models()`, `health_check()`, etc.; each provider implements it
- Provider registry pattern: loads all provider classes from a known module path, keyed by provider name; pipeline code selects by name
- Rate limiting: each provider instance tracks token/request budgets with configurable limits; incoming requests queue if budget exhausted
- AES-GCM chosen over AES-CBC for built-in authentication; nonce stored alongside ciphertext
- Session key: derived from passphrase via PBKDF2/Argon2; stored only in memory, never persisted
- `config_loader.py` extended to: (a) detect encrypted credential file, (b) prompt for decryption key on first load, (c) make decrypted secrets available to provider constructors
- Hot-swap API: `PATCH /api/config/provider` changes active provider; in-flight requests drain on original provider before switch takes effect
- Fallback list: priority-ordered list of provider names in config; on failure, iterate list; log each attempt with latency; escalate to operator if all fail
- No changes to strategy pipeline orchestration — providers are swappable beneath the existing strategy interface

## UX & Interaction Patterns

- First-run: user provides LLM API keys via CLI flag or env var; system encrypts and writes to disk; plaintext never logged or stored
- Runtime: user sends `PATCH /api/config/provider` with new provider name (e.g., `"claude"`) to switch; current cycle completes before switch takes effect
- Config file specifies provider priority list for fallback: `["claude", "deepseek", "openai"]`
- Provider health/status visible via existing API routes

## Cross-Story Dependencies

- Story 1.2 (Unified Interface) depends on Story 1.1 (Credential Store) — provider constructors need API keys loaded from encrypted store
- Story 1.3 (Hot-Swap) depends on Story 1.2 — runtime switching requires the unified interface
- No cross-epic dependencies for Epic 1
