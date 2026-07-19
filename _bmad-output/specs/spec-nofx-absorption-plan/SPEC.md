---
id: SPEC-nofx-absorption-plan
companions: []
sources:
  - "Analysis from 2026-07-18 session — NOFX repo exploration"
---

# NOFX Absorption Plan

## Why

NOFX (NoFxAiOS/nofx) is the most complete open-source AI trading terminal available — 9 exchanges, 9 LLM providers with MCP abstraction, 7-layer risk engine in Go, x402 pay-per-call via Claw402, grid trading, encrypted credentials, 3-layer agent memory, and 81 multi-language docs. crypto-bot has equivalent ambition but gaps in provider abstraction, runtime/LLM security separation, credential encryption, and trading variety (grid, signal overlay). This spec defines which NOFX patterns to absorb, in what order, and which to explicitly reject — turning NOFX from competitor into design reference.

## Capabilities

- **CAP-1**
  - **intent:** User can swap LLM provider mid-strategy without restart. System routes requests through unified AIClient interface with fallback chains.  
  - **success:** Same pipeline cycle runs successfully with GPT-4, then Claude, then DeepSeek without code changes or restart.

- **CAP-2**
  - **intent:** LLM cannot directly place orders — all trade decisions pass through runtime decision engine enforcing position limits, order validation, and circuit breakers.  
  - **success:** LLM-suggested over-limit trade is rejected by engine with logged reason in backtest mode.

- **CAP-3**
  - **intent:** Exchange API keys, wallet secrets, and credentials stored encrypted at rest, decrypted only in-memory per session, with key rotation.  
  - **success:** Store and load exchange API keys successfully; file on disk verified as encrypted (AES-GCM); plaintext never written to disk.

- **CAP-4**
  - **intent:** User can configure price-level grid with automatic state transitions (empty→pending→filled), position sizing, and auto-hedging.  
  - **success:** Grid strategy passes 10+ backtest cycles with correct fill records and state transitions matching expected grid behavior.

- **CAP-5**
  - **intent:** External signals (Vergex, TradingView webhooks, custom feeds) flow into crypto-bot as typed events consumed by active strategies, influencing trade decisions.  
  - **success:** At least one external signal type processed through event_bus.py and consumed by a running strategy in test mode.

- **CAP-6**
  - **intent:** Development team (agent and human) operates with consistent memory hygiene — understanding what belongs in session context vs daily notes vs long-term memory.  
  - **success:** Guidance doc exists, reviewed, applied in practice — measurable by agent correctly retrieving cross-session context without stale assumptions.

## Constraints

- **Must stay Python-based.** crypto-bot ecosystem is Python; introducing Go runtime splits dev focus, complicates deployment (Docker needs both runtimes), and fragments testing. All absorbed patterns must have Python-native implementations.
- **Must remain OpenClaw-native.** NOFXi agent is embedded in Go process with its own planner. crypto-bot uses OpenClaw as agent runtime. Agent memory patterns from NOFX adapt as guidance, not ported code.
- **x402 pay-per-call deferred.** Requires USDC wallet, Claw402 gateway integration, and Base L2 on-chain infrastructure. High complexity for uncertain gain over existing LLM proxy (9router). Revisit only if LLM proxy cost becomes prohibitive or pay-per-call model becomes standard.

## Non-goals

- Porting Go backend to Python or replacing crypto-bot architecture with NOFX's.
- Adding all 9 NOFX exchange integrations in a single effort (exchange expansion is separate).
- Building a full 81-doc documentation suite before addressing software gaps.
- Replacing OpenClaw agent runtime with a custom Go agent.
- Implementing on-chain payment (x402) in the near term.

## Success signal

crypto-bot has:
1. A working MCP provider abstraction through which any supported LLM can be swapped mid-strategy without restart — demonstrated by running the same pipeline cycle with GPT-4, then Claude, then DeepSeek.
2. A runtime decision guard that prevents the LLM from placing orders that violate position/risk limits — demonstrated by a rejected over-limit trade in backtest mode.
3. An encrypted credential store with a key rotation mechanism — demonstrated by storing and loading exchange API keys without plaintext on disk.
4. A grid trading strategy passing 10+ backtest cycles with correct fill/state transitions.
5. A signal overlay processing at least one external signal type and passing it to strategy engine.

## Assumptions

- LLM provider ecosystem will continue to diversify (more models, more APIs); abstraction pays off more over time.
- Existing strategy_registry interface (`StrategyBase`) can accommodate grid trading without breaking existing strategies.
- `event_bus.py` pub/sub model is sufficient for signal overlay without replacement.
- Python cryptography (Fernet) provides adequate encryption for credential at rest without hardware security module.

## Open Questions

- CAP-1: Should provider abstraction include a cost-optimization router (auto-pick cheapest model that meets quality threshold), or just round-robin/priority fallback?
- CAP-2: Should the decision engine live in a separate process (multiprocessing.Process) or a thread with strict GIL-aware locking? Go benefits from goroutines — what's the Python-equivalent safety model?
- CAP-4: Grid trading needs persistent state between restarts (price levels, fill status). Should state live in SQLite via existing store or in-memory with recovery from exchange open orders?
- CAP-5: Signal source authentication — TradingView webhooks need HMAC verification. Should crypto-bot implement this or delegate to a reverse proxy?

## Derivation Order

Implementation priority based on leverage vs cost:

1. **CAP-3 (encrypted credentials)** — quickest win. Integrate into `config_loader.py`. Estimated: 1-2 days.
2. **CAP-1 (MCP provider abstraction)** — highest leverage. Design interface, port existing providers, add fallback. Estimated: 3-5 days.
3. **CAP-4 (grid trading)** — standalone plugin, no architectural dependencies. Estimated: 2-3 days.
4. **CAP-5 (signal overlay)** — depends on event_bus.py which exists. Estimated: 2-3 days.
5. **CAP-2 (runtime separation)** — requires refactoring `agent_desk.py` and `paper_engine.py`. Most complex. Estimated: 5-7 days.
6. **CAP-6 (agent memory guide)** — lowest effort, documentation only. Estimated: 0.5 day.

Total: ~14-21 days est. for full absorption.
