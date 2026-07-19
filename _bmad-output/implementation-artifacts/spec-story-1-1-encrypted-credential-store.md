---
title: 'Story 1.1 — Encrypted Credential Store'
type: 'feature'
created: '2026-07-19'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: e033fab
context:
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
  - '_bmad-output/planning-artifacts/epics.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Three plaintext credential surfaces in codebase (`.env` LLM_API_KEY, `.ai-trader-credentials.json` email/password/token on disk) with zero encryption at-rest. No crypto dependencies.

**Approach:** Create `core/credential_store.py` using `cryptography.Fernet` (AES-GCM) to encrypt/decrypt/load/save/rotate credentials. Integrate into existing `ai_trader_client.py` and `llm_client.py` credential paths. Master key supplied via env var `CREDENTIAL_STORE_KEY` (base64-encoded, never stored with encrypted payload).

## Boundaries & Constraints

**Always:**
- Use `cryptography` library (Fernet = AES-128-CBC + HMAC, enough for this scope)
- Master key loaded from `CREDENTIAL_STORE_KEY` env var at startup; if absent, generate on first use, print to stdout, require user to set it
- Envelope format: JSON file with `version`, `ciphertext`, `nonce` fields (Fernet handles this internally)
- Existing `.env` + `.ai-trader-credentials.json` must still be readable during migration (backward compat one release)
- All existing tests pass (191)
- Python-native, no external KMS, no Go, no subprocess

**Block If:**
- User cannot set `CREDENTIAL_STORE_KEY` env var (no other key management mechanism for v1)
- Migration path unclear for existing plaintext credentials

**Never:**
- No cloud KMS/HashiCorp Vault/AWS Secrets Manager integration in this story
- No TPM/HSM
- No encryption at rest that requires network

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh install, no key, no credentials | No `CREDENTIAL_STORE_KEY`, no credential file | Generate master key, encrypt and write first credential, print key to stdout | None |
| Normal startup with key | `CREDENTIAL_STORE_KEY` set, encrypted file exists | Decrypt credentials in-memory, return dict with all secrets | `CryptographyError` → logged, HALT |
| Key rotation | Old key + existing encrypted file | Decrypt with old key, re-encrypt with new key, overwrite file | Backup old file before overwrite |
| Corrupt encrypted file | File has invalid Fernet token | Log "Credential store corrupted", ask user to restore from backup or re-configure | `InvalidToken` caught, graceful message |
| Missing key at startup | No `CREDENTIAL_STORE_KEY`, encrypted file exists | Fail with clear message: "Set CREDENTIAL_STORE_KEY — key was printed on first credential write" | `KeyError` → log + exit |
| Get credential by key | Store has `llm_api_key` | Return decrypted value | `KeyError` if key missing |
| Migration from plaintext | Plaintext `.ai-trader-credentials.json` + `.env` exist | On first write, read plaintext, encrypt, write, delete plaintext | If encrypt fails, don't delete plaintext |
| Concurrent access | Two threads call load_credentials simultaneously | Thread-safe via `threading.Lock` | N/A |
| Empty credential file | Empty dict `{}` encrypted | Load returns empty dict, first write creates it | N/A |

</intent-contract>

## Code Map

- `core/credential_store.py` -- NEW: encrypt/decrypt/load/save/rotate/ensure_initialized
- `core/ai_trader_client.py` -- MODIFY: replace `json.load`/`json.dump` with `credential_store` calls in `load_credentials()` / `save_credentials()`; keep fallback to plaintext (read plaintext → encrypt → write → delete plaintext)
- `core/llm_client.py` -- MODIFY: wrap `os.getenv('LLM_API_KEY')` with `credential_store.load('llm_api_key')`, add fallback to env var
- `core/config_loader.py` -- MODIFY: optional — expose `credential_store` init hook; only if ai_trader_client init path passes through config_loader
- `pyproject.toml` -- ADD: `cryptography>=42.0.0`
- `tests/unit/test_credential_store.py` -- NEW: 8+ tests covering I/O matrix
- `.gitignore` -- ADD: `*.credential-store.key` (prevent key file commits)

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml` -- add `cryptography>=42.0.0` dependency -- needed for Fernet AES-GCM
- [ ] `core/credential_store.py` -- create CredentialStore class with encrypt/decrypt/load/save/rotate/ensure_initialized -- core module
- [ ] `core/ai_trader_client.py` -- integrate credential_store into `load_credentials()` / `save_credentials()` with plaintext migration -- encrypt existing plaintext credentials
- [ ] `core/llm_client.py` -- add `LLM_API_KEY` to credential_store, fallback to env var -- unified key resolution
- [ ] `tests/unit/test_credential_store.py` -- write 8+ tests for I/O matrix scenarios -- verify correctness
- [ ] `.gitignore` -- add `*.credential-store.key` -- prevent accidental key commits

**Acceptance Criteria:**
- Given an existing `.ai-trader-credentials.json` plaintext file, when `credential_store` initializes, then it encrypts the file and deletes the plaintext copy
- Given `CREDENTIAL_STORE_KEY` is absent, when a credential is first written, then the key is generated and printed to stdout
- Given a corrupt encrypted file, when `credential_store.load()` is called, then it raises `CredentialStoreError` with a clear message
- Given the store is initialized, when `credential_store.get('llm_api_key')` is called, then the plaintext value is returned
- Given the store has no key, when `credential_store.get('nonexistent')` is called, then `KeyError` is raised

## Spec Change Log

<!-- Empty until first review loopback -->

## Review Triage Log

<!-- Empty until first review pass -->

## Design Notes

**Key management strategy:** Single env var `CREDENTIAL_STORE_KEY` as base64-encoded 32-byte Fernet key. On first use, generate key via `Fernet.generate_key()`, print it to stdout, require user to set it as env var for subsequent runs. This avoids filesystem key storage (no "key stored next to lock").

**Migration flow:**
1. Start → no `CREDENTIAL_STORE_KEY`, plaintext files exist → generate key, encrypt in-memory → write encrypted files → delete plaintext → print key → exit (with instruction to set env var)
2. Start → `CREDENTIAL_STORE_KEY` set → decrypt → continue (no migration needed)

**Thread safety:** `threading.Lock` in `CredentialStore.load()` — crypt context stores decrypted dict in memory, lock only on first load and on save.

**Class interface sketch (3 methods public):**
```python
class CredentialStore:
    def __init__(self, key_env_var: str = "CREDENTIAL_STORE_KEY", store_path: str = ".credentials.enc"): ...
    def get(self, key: str) -> str: ...
    def set(self, key: str, value: str): ...
    def rotate(self, new_key: bytes): ...
```

No `save()` exposed — mutations are auto-persisted on `set()`.

## Verification

**Commands:**
- `cd /home/node/.openclaw/workspace/crypto-bot && uv run pytest tests/unit/test_credential_store.py -v` -- expected: 8+ passed
- `cd /home/node/.openclaw/workspace/crypto-bot && uv run pytest -x --tb=short` -- expected: 191+ passed (no regressions)
- `cd /home/node/.openclaw/workspace/crypto-bot && uv run python -c "from core.credential_store import CredentialStore; cs = CredentialStore(); cs.set('test', 'val'); assert cs.get('test') == 'val'; print('OK')"` -- expected: integration smoke test passes

**Manual checks:**
- Verify `.ai-trader-credentials.json` is deleted after migration (backup first)
- Verify `.env` LLM_API_KEY reading still works via credential_store fallback
