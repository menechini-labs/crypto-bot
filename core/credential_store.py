import os
import json
import threading
from pathlib import Path
from cryptography.fernet import Fernet

class CredentialStoreError(Exception):
    """Base exception for credential store."""

class CredentialStore:
    """Encrypted credential store using Fernet (AES-128-CBC + HMAC).
    
    Stores credentials in a JSON file with all values encrypted.
    Master key from CREDENTIAL_STORE_KEY env var (base64 Fernet key).
    Thread-safe via threading.Lock.
    """

    STORE_FILENAME = ".credentials.enc"
    KEY_ENV_VAR = "CREDENTIAL_STORE_KEY"

    def __init__(self, store_path: str | None = None, key_env_var: str | None = None):
        self._store_path = Path(store_path or self.STORE_FILENAME)
        self._key_env_var = key_env_var or self.KEY_ENV_VAR
        self._lock = threading.Lock()
        self._fernet: Fernet | None = None
        self._cache: dict[str, str] | None = None

    # --- Public API ---

    def get(self, key: str) -> str:
        """Get a decrypted credential. Raises KeyError if missing."""
        self._ensure_loaded()
        if key not in self._cache:
            raise KeyError(f"Credential '{key}' not found in store")
        return self._cache[key]

    def set(self, key: str, value: str):
        """Set and immediately persist a credential."""
        self._ensure_loaded()
        self._cache[key] = value
        self._flush()

    def delete(self, key: str):
        """Delete a credential."""
        self._ensure_loaded()
        self._cache.pop(key, None)
        self._flush()

    def keys(self) -> list[str]:
        """List all credential keys."""
        self._ensure_loaded()
        return list(self._cache.keys())

    def rotate(self, new_key: bytes):
        """Re-encrypt store with a new Fernet key."""
        with self._lock:
            old_data = self._decrypt_file()
            self._fernet = Fernet(new_key)
            self._write_encrypted(old_data)
            # Update env so subsequent starts use the new key
            os.environ[self._key_env_var] = new_key.decode()

    def exists(self) -> bool:
        """Check if encrypted store file exists on disk."""
        return self._store_path.exists()

    @property
    def key_configured(self) -> bool:
        """Check if CREDENTIAL_STORE_KEY env var is set."""
        return self._key_env_var in os.environ

    # --- Migration helper ---

    def migrate_from_plaintext(self, source_path: str, source_loader=None):
        """Read plaintext credentials file, encrypt it, write store, delete source.
        
        If source_loader is callable, it receives (path) and returns dict.
        Otherwise, tries json.load.
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        if source_loader:
            data = source_loader(str(source))
        else:
            import json as _json
            data = _json.loads(source.read_text())
        
        if not isinstance(data, dict):
            raise ValueError("Source data must be a dict")
        
        with self._lock:
            self._ensure_ready()
            self._cache = {k: str(v) for k, v in data.items()}
            self._write_encrypted(self._cache)
        
        # Decrypt once to verify before deleting source
        self._ensure_loaded()
        source.unlink()

    # --- Internal ---

    def _ensure_ready(self):
        """Make sure Fernet is initialized (key loaded or generated)."""
        if self._fernet is not None:
            return
        
        env_key = os.environ.get(self._key_env_var)
        if env_key:
            self._fernet = Fernet(env_key.encode())
        else:
            # Generate key on first use, print it, and set in env for this session
            raw_key = Fernet.generate_key()
            print(f"🔑 Generated new credential store key. Set it as environment variable:")
            print(f"    export {self._key_env_var}={raw_key.decode()}")
            print(f"Store this key securely — without it, credentials cannot be recovered.")
            os.environ[self._key_env_var] = raw_key.decode()
            self._fernet = Fernet(raw_key)

    def _ensure_loaded(self):
        """Ensure store is decrypted and cached in memory."""
        if self._cache is not None:
            return
        self._ensure_ready()
        with self._lock:
            if self._cache is not None:
                return
            if self._store_path.exists():
                data = self._decrypt_file()
                self._cache = data
            else:
                self._cache = {}

    def _decrypt_file(self) -> dict[str, str]:
        """Read and decrypt the store file. Returns dict."""
        try:
            encrypted_data = self._store_path.read_bytes()
            decrypted = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted)
        except Exception as e:
            raise CredentialStoreError(
                f"Failed to decrypt credential store. "
                f"Check {self._key_env_var} is correct and store is not corrupted."
            ) from e

    def _flush(self):
        """Write current cache to encrypted file."""
        with self._lock:
            self._ensure_ready()
            self._write_encrypted(self._cache)

    def _write_encrypted(self, data: dict):
        """Encrypt and write dict to store file."""
        payload = json.dumps(data).encode()
        encrypted = self._fernet.encrypt(payload)
        self._store_path.write_bytes(encrypted)
