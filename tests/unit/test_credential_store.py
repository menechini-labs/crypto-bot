"""Tests for Encrypted Credential Store."""

import json
import os
import threading

import pytest

from core.credential_store import CredentialStore, CredentialStoreError
from cryptography.fernet import Fernet


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_store_path(tmp_path):
    """Return a path inside a temp dir so tests don't clobber each other."""
    return tmp_path / ".credentials.enc"


@pytest.fixture
def fernet_key():
    return Fernet.generate_key()


@pytest.fixture
def cred_store(fernet_key, tmp_path, monkeypatch):
    """Create a CredentialStore with a known key and isolated path."""
    monkeypatch.setenv("CREDENTIAL_STORE_KEY", fernet_key.decode())
    store = CredentialStore(
        store_path=str(tmp_path / ".credentials.enc"),
        key_env_var="CREDENTIAL_STORE_KEY",
    )
    return store


@pytest.fixture(autouse=True)
def _cleanup_global_path(monkeypatch, tmp_path):
    """Redirect the default .credentials.enc path to a temp dir so tests
    don't accidentally read/write the real project root."""
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_set_and_get(cred_store):
    """Set a credential then retrieve it."""
    cred_store.set("llm_api_key", "sk-test123")
    assert cred_store.get("llm_api_key") == "sk-test123"


def test_get_missing_key_raises_keyerror(cred_store):
    """Getting a nonexistent key raises KeyError."""
    with pytest.raises(KeyError, match="not found"):
        cred_store.get("nonexistent")


def test_key_generation_on_first_use(tmp_path, monkeypatch):
    """When no env var is set, a key is generated and printed."""
    monkeypatch.chdir(tmp_path)
    # Remove CREDENTIAL_STORE_KEY from env
    monkeypatch.delenv("CREDENTIAL_STORE_KEY", raising=False)
    store = CredentialStore(store_path=str(tmp_path / ".credentials.enc"))
    store.set("test", "value")
    # Key should now be in env
    assert "CREDENTIAL_STORE_KEY" in os.environ
    assert store.get("test") == "value"


def test_load_with_valid_key(cred_store):
    """Write some data, then create a new instance with the same key and verify it loads."""
    cred_store.set("key_a", "val_a")
    cred_store.set("key_b", "val_b")

    store2 = CredentialStore(
        store_path=str(cred_store._store_path),
        key_env_var="CREDENTIAL_STORE_KEY",
    )
    assert store2.get("key_a") == "val_a"
    assert store2.get("key_b") == "val_b"
    assert sorted(store2.keys()) == sorted(["key_a", "key_b"])


def test_persist_and_reload(fernet_key, tmp_path, monkeypatch):
    """Write data, destroy instance, create new one — data survives."""
    monkeypatch.setenv("CREDENTIAL_STORE_KEY", fernet_key.decode())
    path = tmp_path / ".credentials.enc"

    s1 = CredentialStore(store_path=str(path))
    s1.set("k", "v")

    s2 = CredentialStore(store_path=str(path))
    assert s2.get("k") == "v"
    assert "k" in s2.keys()



def test_delete_credential(cred_store):
    cred_store.set("temp", "temp_val")
    assert cred_store.get("temp") == "temp_val"
    cred_store.delete("temp")
    with pytest.raises(KeyError):
        cred_store.get("temp")


def test_rotate_key(cred_store):
    cred_store.set("secret", "original")
    old_key = os.environ["CREDENTIAL_STORE_KEY"]

    new_key = Fernet.generate_key()
    cred_store.rotate(new_key)

    # New store instance with same env (now updated by rotate) works
    new_store = CredentialStore(
        store_path=str(cred_store._store_path),
        key_env_var="CREDENTIAL_STORE_KEY",
    )
    assert new_store.get("secret") == "original"
    # Env var updated to new key
    assert os.environ["CREDENTIAL_STORE_KEY"] != old_key


def test_migrate_from_plaintext_json(fernet_key, tmp_path, monkeypatch):
    monkeypatch.setenv("CREDENTIAL_STORE_KEY", fernet_key.decode())
    plaintext_path = tmp_path / "plaintext.json"
    data = {"api_key": "sk-abc123", "secret": "s3cret"}
    plaintext_path.write_text(json.dumps(data))

    store = CredentialStore(store_path=str(tmp_path / ".credentials.enc"))
    store.migrate_from_plaintext(str(plaintext_path))

    assert store.get("api_key") == "sk-abc123"
    assert store.get("secret") == "s3cret"
    # Plaintext file should be deleted
    assert not plaintext_path.exists()


def test_corrupt_file_raises_error(fernet_key, tmp_path, monkeypatch):
    monkeypatch.setenv("CREDENTIAL_STORE_KEY", fernet_key.decode())
    path = tmp_path / ".credentials.enc"
    # Write garbage
    path.write_bytes(b"not-fernnet-encrypted-data")

    store = CredentialStore(store_path=str(path))
    # Trigger decrypt on any operation that loads
    with pytest.raises(CredentialStoreError):
        store.get("anything")


def test_thread_safety(cred_store):
    """Concurrent set/get operations don't crash or lose data."""
    n = 50
    errors = []

    def writer(idx):
        try:
            cred_store.set(f"k{idx}", f"v{idx}")
        except Exception as e:
            errors.append(e)

    def reader(idx):
        try:
            val = cred_store.get(f"k{idx}")
            assert val == f"v{idx}" or val is None
        except KeyError:
            pass  # might not have been written yet
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(n):
        t = threading.Thread(target=writer, args=(i,))
        threads.append(t)
        t.start()
        # Also start readers interleaved
        tr = threading.Thread(target=reader, args=(i,))
        threads.append(tr)
        tr.start()

    for t in threads:
        t.join()

    assert not errors, f"Thread safety errors: {errors}"
    # Verify all written values readable
    for i in range(n):
        assert cred_store.get(f"k{i}") == f"v{i}"


def test_keys_method(cred_store):
    cred_store.set("a", "1")
    cred_store.set("b", "2")
    cred_store.set("c", "3")
    keys = cred_store.keys()
    assert sorted(keys) == ["a", "b", "c"]


def test_exists_property(cred_store, tmp_path):
    assert not cred_store.exists()
    cred_store.set("x", "y")
    assert cred_store.exists()

def test_key_configured_property(cred_store):
    assert cred_store.key_configured is True

def test_key_not_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("CREDENTIAL_STORE_KEY", raising=False)
    store = CredentialStore(store_path=str(tmp_path / ".credentials.enc"))
    assert store.key_configured is False

def test_migrate_from_plaintext_missing_file(cred_store):
    with pytest.raises(FileNotFoundError):
        cred_store.migrate_from_plaintext("/nonexistent/file.json")


def test_migrate_from_plaintext_non_dict(fernet_key, tmp_path, monkeypatch):
    monkeypatch.setenv("CREDENTIAL_STORE_KEY", fernet_key.decode())
    plaintext_path = tmp_path / "bad.json"
    plaintext_path.write_text(json.dumps(["not", "a", "dict"]))
    store = CredentialStore(store_path=str(tmp_path / ".credentials.enc"))
    with pytest.raises(ValueError, match="must be a dict"):
        store.migrate_from_plaintext(str(plaintext_path))
