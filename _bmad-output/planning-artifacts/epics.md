---
stepsCompleted:
  - "step-01-validate-prerequisites"
  - "step-02-design-epics"
inputDocuments:
  - "_bmad-output/specs/spec-nofx-absorption-plan/SPEC.md"
---

# crypto-bot - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for crypto-bot, decomposing the requirements from the NOFX absorption SPEC into implementable stories for improving the existing project.

## Requirements Inventory

### Functional Requirements

FR1: System must provide unified LLM provider interface supporting hot-swappable providers (OpenAI, DeepSeek, Claude, Gemini, Qwen) with per-model rate limits and fallback chains — replacing current llm_client.py switch-case with pluggable provider registry.
FR2: System must implement runtime decision engine that validates all trade orders against position limits, hard constraints, and circuit breakers before execution, preventing LLM from directly placing orders.
FR3: System must encrypt all credentials (API keys, exchange secrets, wallet keys) at rest using AES-GCM, decrypted only in-memory per session with key rotation support.
FR4: System must provide grid trading strategy as plugin with configurable price levels, state transitions (empty→pending→filled), position sizing, and auto-hedging.
FR5: System must process external signals (Vergex, TradingView webhooks, custom feeds) as typed events through event_bus.py consumed by active strategies.
FR6: System must include guidance document mapping NOFXi three-layer memory concepts to OpenClaw equivalents for consistent memory hygiene.

### NonFunctional Requirements

NFR1: All implementation must be Python-native — no Go dependencies introduced.
NFR2: System must remain OpenClaw-native for agent runtime — agent memory patterns from NOFX adapted as guidance only, not ported code.
NFR3: x402 pay-per-call deferred — not implemented until LLM proxy cost becomes prohibitive or model standardizes.
NFR4: Existing tests (191 passing) must continue passing after each change.
NFR5: Backward compatibility with existing strategies (scalping, LLM-strategy) must be maintained.

### Additional Requirements

- Existing strategy_registry interface (`StrategyBase`) must accommodate grid trading without breaking existing strategies (scalping, LLM-strategy).
- `event_bus.py` pub/sub model must be sufficient for signal overlay — no replacement needed.
- Encrypted credentials must integrate into existing `config_loader.py`.
- Docker deployment must remain single-runtime (Python only).

### UX Design Requirements

(None — no UX design document exists.)

### FR Coverage Map

FR1 (LLM provider interface): Epic 1
FR2 (Runtime decision engine): Epic 2
FR3 (Encrypted credentials): Epic 1
FR4 (Grid trading): Epic 3
FR5 (Signal overlay): Epic 4
FR6 (Memory hygiene guide): Epic 5

## Epic List

### Epic 1: Fundação Segura de Múltiplos Providers
User can configure multiple LLM providers with encrypted credentials and hot-swap between them mid-strategy without restart.
**FRs covered:** FR1, FR3

### Epic 2: Segurança de Execução (Runtime Decision Engine)
User is protected from LLM placing orders that violate position limits or risk rules — LLM suggests, engine validates and executes.
**FRs covered:** FR2

### Epic 3: Grid Trading Strategy
User can configure grid trading with configurable price levels, automatic state transitions, and portfolio-aware position sizing.
**FRs covered:** FR4

### Epic 4: Processamento de Sinais Externos
User can feed external signals (TradingView webhooks, Vergex, custom feeds) into crypto-bot as typed events consumed by active strategies.
**FRs covered:** FR5

### Epic 5: Guia de Higiene de Memória do Agente
Team (agent + human) operates with consistent memory hygiene mapped to OpenClaw paradigms.
**FRs covered:** FR6

## Epic 1: Fundação Segura de Múltiplos Providers

User can configure multiple LLM providers with encrypted credentials and hot-swap between them mid-strategy without restart.
**FRs covered:** FR1, FR3

### Story 1.1: Encrypted Credential Store

As a system administrator / user,
I want exchange API keys and LLM provider credentials stored encrypted at rest with AES-GCM, decrypted only in-memory per session,
So that compromising disk does not expose plaintext secrets.

**Acceptance Criteria:**

**Given** a fresh config directory with no credentials file
**When** the user provides a plaintext API key via CLI or env
**Then** the key is encrypted with AES-GCM and written to disk
**And** the plaintext key is never written to disk

**Given** an existing encrypted credentials file
**When** crypto-bot starts and decrypts it using the session key
**Then** credentials are available in-memory for the session lifetime
**And** the file on disk verifies as AES-GCM ciphertext

**Given** a session key needs rotation
**When** the user invokes rotate-credentials command
**Then** old file is re-encrypted with new key
**And** the old ciphertext is overwritten

### Story 1.2: Unified LLM Provider Interface

As a developer / user,
I want a unified abstract interface for LLM providers with pluggable registry supporting OpenAI, DeepSeek, Claude, Gemini, and Qwen,
So that I can add new providers or fallback between them without modifying core pipeline code.

**Acceptance Criteria:**

**Given** the current llm_client.py has a switch-case per provider
**When** the new interface is implemented
**Then** each provider is a self-contained class implementing a common abstract base
**And** the provider registry discovers and loads providers dynamically

**Given** a provider call fails (network error, rate limit, auth failure)
**When** a fallback chain is configured
**Then** the system tries the next provider in the chain automatically
**And** logs the fallback reason and latency per provider

**Given** a new provider (e.g. Qwen) needs to be added
**When** a developer writes a provider class implementing the abstract interface
**Then** no changes to llm_client.py or pipeline code are needed
**And** the provider is immediately available for use

**Given** a provider is rate-limited
**When** the interface receives a request
**Then** it respects per-model rate limits (tokens/min, requests/min)
**And** queues or defers when tokens exceed the budget

### Story 1.3: Hot-Swap Provider Mid-Strategy

As a trader / operator,
I want to switch the active LLM provider while the pipeline is running without restarting the server,
So that I can change models based on cost, latency, or quality needs without downtime.

**Acceptance Criteria:**

**Given** the pipeline is running with provider "openai"
**When** I send a PATCH /api/config/provider request with provider "claude"
**Then** subsequent pipeline cycles use Claude
**And** current in-flight requests complete with original provider before switching

**Given** the provider interface has multiple configured providers
**When** I configure a priority fallback list [claude, deepseek, openai]
**Then** Claude is tried first
**And** if Claude fails, DeepSeek is automatically tried
**And** only if both fail, OpenAI is used

**Given** a hot-swap occurs mid-strategy
**When** the new provider returns a response
**Then** the response is logged with provider identifier
**And** the switch is reflected in the pipeline view / status endpoint

## Epic 2: Segurança de Execução (Runtime Decision Engine)

User is protected from LLM placing orders that violate position limits or risk rules — LLM suggests, engine validates and executes.
**FRs covered:** FR2

### Story 2.1: Runtime Decision Engine Core

As a system / risk manager,
I want a dedicated decision engine that enforces position limits, max drawdown, and circuit breakers before any order execution,
So that no single LLM suggestion can cause catastrophic loss even if the model goes rogue.

**Acceptance Criteria:**

**Given** engine is configured with max_position=1 BTC
**When** a trade suggestion would result in 1.5 BTC total position
**Then** the engine rejects the order
**And** logs the rejection reason as "position limit exceeded"

**Given** the portfolio is down 15% (circuit breaker threshold)
**When** any trade suggestion arrives
**Then** the engine halts all trading
**And** logs "circuit breaker active — max drawdown exceeded"

**Given** engine configuration includes per-exchange limits
**When** a trade exceeds the exchange's max order size
**Then** the engine rejects and logs "order exceeds exchange limit"

### Story 2.2: LLM Suggestion → Engine Validation Pipeline

As a trader,
I want the LLM to propose trades which are then validated by the runtime engine before execution,
So that the LLM acts as advisor, not executor, with risk controls in the middle.

**Acceptance Criteria:**

**Given** the pipeline is running with LLM strategy active
**When** the LLM returns a trade suggestion (buy 0.5 BTC at market)
**Then** the suggestion is passed to the runtime decision engine before any order is placed
**And** the engine validates against position limits, drawdown, and exchange rules

**Given** the engine approves a suggestion
**When** validation passes
**Then** the order is executed via paper_engine (or real exchange)
**And** the pipeline logs "LLM suggestion → engine approved → order placed"

**Given** the engine rejects a suggestion
**When** any validation fails
**Then** the order is never sent to the exchange
**And** the pipeline logs "LLM suggestion → engine rejected: [reason]"

**Given** the engine process crashes or times out
**When** a suggestion arrives
**Then** a default-safe behavior applies (reject all trades)
**And** an alert is logged

### Story 2.3: Over-Limit Rejection + Dashboard Visibility

As a trader / operator,
I want rejected trades to appear in the pipeline view with clear reason, not just disappear silently,
So that I can monitor and tune risk parameters without tailing server logs.

**Acceptance Criteria:**

**Given** the engine rejects a trade
**When** the pipeline cycle completes
**Then** the rejection appears in GET /api/pipeline/status response
**And** includes fields: suggestion (original LLM proposal), reason (engine rejection reason), timestamp

**Given** rejected trades accumulate
**When** I view the PipelineView dashboard
**Then** rejected trades are listed in a "Rejected Orders" section
**And** each entry shows reason, suggested price/size, timestamp

**Given** a trade was rejected due to position limit
**When** I check the rejection history
**Then** the current position limit is displayed alongside the rejection reason

## Epic 3: Grid Trading Strategy

User can configure grid trading with configurable price levels, automatic state transitions, and portfolio-aware position sizing.
**FRs covered:** FR4

### Story 3.1: Grid Configuration + State Machine

As a trader,
I want to configure a grid trading strategy with price levels, state transitions (empty→pending→filled), and position sizing,
So that I can automate range-bound trading without manual order management.

**Acceptance Criteria:**

**Given** I configure grid price levels [90000, 92000, 94000, 96000, 98000, 100000]
**When** I activate the strategy
**Then** each level initializes in "empty" state
**And** the grid registers as a plugin in strategy_registry

**Given** price crosses a grid level
**When** price moves past a configured level
**Then** the level transitions to "pending" (preparing order)
**And** then to "filled" once the order executes

**Given** a filled level needs unwinding
**When** price moves back past the level in the opposite direction
**Then** the level transitions back through pending → empty
**And** a reverse order is placed to close the position

**Given** grid config includes position sizing per level
**When** a level triggers an order
**Then** the order size respects the per-level allocation
**And** total portfolio allocation across all filled levels does not exceed configured max

### Story 3.2: Grid Auto-Hedging + Portfolio Awareness

As a trader,
I want the grid strategy to be portfolio-aware and support auto-hedging,
So that concurrent strategies (scalping, LLM) don't conflict with grid positions.

**Acceptance Criteria:**

**Given** grid strategy is running alongside a scalping strategy
**When** both strategies reference same asset (e.g. BTC/USDT)
**Then** grid accounts for positions opened by scalping when computing available balance for grid levels
**And** total exposure across all active strategies does not exceed portfolio limits

**Given** grid has 3 filled levels (long, long, short)
**When** I enable auto-hedging
**Then** net exposure is calculated across all levels
**And** a hedge order is placed to neutralize delta beyond a configurable threshold

**Given** price gaps through multiple grid levels quickly
**When** levels transition from empty → pending → filled rapidly
**Then** the system batches or throttles order placement to avoid slippage
**And** logs skipped levels when price moves through them before execution

### Story 3.3: Grid Persistence + Recovery

As a trader,
I want grid state to survive restarts,
So that a server restart doesn't lose active grid positions or require manual reconciliation.

**Acceptance Criteria:**

**Given** grid has 4 filled levels and the server restarts
**When** the strategy loads on startup
**Then** it reads persistent state from SQLite
**And** restores each level to its previous state (filled/pending/empty)
**And** reconciles against exchange open orders

**Given** an exchange order was filled while server was down
**When** recovery runs
**Then** grid detects the discrepancy between persisted state and exchange state
**And** updates local state to match exchange reality
**And** logs the reconciliation

**Given** no persistent state exists (fresh start)
**When** grid strategy initializes
**Then** it starts with all levels in "empty" state
**And** waits for price conditions before transitioning

## Epic 4: Processamento de Sinais Externos

User can feed external signals (TradingView webhooks, Vergex, custom feeds) into crypto-bot as typed events consumed by active strategies.
**FRs covered:** FR5

### Story 4.1: Signal Event Type + event_bus Integration

As a developer,
I want external signals represented as typed events in event_bus.py,
So that any strategy can subscribe and react to signals without coupling to signal sources.

**Acceptance Criteria:**

**Given** event_bus.py exists with pub/sub model
**When** I define a SignalEvent type with fields: source, asset, direction, confidence, metadata
**Then** any strategy can subscribe to signal events via event_bus.subscribe("signal")
**And** receive typed payloads without parsing raw data

**Given** multiple signal sources send events
**When** a strategy subscribes to "signal"
**Then** it receives events from all sources
**And** can filter by source or confidence in its handler

**Given** no strategy subscribes to signal events
**When** a signal event is published
**Then** the event is silently dropped (no crash, no memory leak)
**And** a debug-level log records the dropped event

### Story 4.2: TradingView Webhook Receiver

As a trader,
I want to receive TradingView webhook alerts as signal events,
So that TradingView strategies can influence crypto-bot decisions.

**Acceptance Criteria:**

**Given** a POST /api/signals/tradingview endpoint exists
**When** a TradingView webhook payload arrives (JSON with symbol, action, price)
**Then** the payload is validated and parsed into a SignalEvent
**And** published to event_bus

**Given** TradingView webhook includes HMAC signature header
**When** the endpoint receives a request
**Then** it validates the HMAC against the shared secret
**And** rejects (401) if signature is invalid
**And** returns 200 OK only on valid signature

**Given** the payload is malformed (missing required fields)
**When** POST /api/signals/tradingview is called
**Then** the endpoint returns 400 Bad Request
**And** logs the validation error

### Story 4.3: Strategy Consumption of Signals

As a strategy developer,
I want to consume signal events within active strategies (scalping, grid, LLM),
So that external signals can influence or override strategy decisions.

**Acceptance Criteria:**

**Given** a strategy subscribes to signal events
**When** a signal event with confidence >= 0.8 arrives for BTC/USDT
**Then** the strategy adjusts its next trade decision based on the signal direction
**And** logs "signal consumed: [source] → [direction]" in pipeline output

**Given** a signal event with low confidence (< 0.3) arrives
**When** a strategy receives it
**Then** the strategy may optionally ignore it
**And** logs "signal ignored: confidence below threshold"

**Given** conflicting signals arrive rapidly for same asset
**When** a strategy evaluates them
**Then** it uses the most recent signal with highest confidence
**And** logs the conflict resolution

## Epic 5: Guia de Higiene de Memória do Agente

Team (agent + human) operates with consistent memory hygiene mapped to OpenClaw paradigms.
**FRs covered:** FR6

### Story 5.1: NOFXi Memory Concepts → OpenClaw Mapping Guide

As a developer / agent operator,
I want a guidance document that maps NOFXi's three-layer memory (chatHistory, TaskState, ExecutionState) to OpenClaw equivalents,
So that the team maintains consistent memory hygiene without porting the NOFXi architecture.

**Acceptance Criteria:**

**Given** the document is created at docs/agent-memory-hygiene.md
**When** a team member reads it
**Then** it clearly maps:
  - chatHistory → OpenClaw session context (short-term, per-conversation)
  - TaskState → OpenClaw daily notes (memory/YYYY-MM-DD.md) + active goal state
  - ExecutionState → OpenClaw MEMORY.md (long-term curated knowledge)
**And** provides concrete examples of what belongs in each layer and what doesn't

**Given** the document includes anti-patterns
**When** a team member reads it
**Then** common mistakes are listed (e.g., putting execution state in chatHistory, mixing task state with permanent memory)
**And** the fix for each anti-pattern is described

**Given** the document is reviewed
**When** a team member follows it for one week
**Then** cross-session context retrieval should show fewer stale assumptions
**And** the agent should correctly distinguish between transient conversation context and permanent decisions
