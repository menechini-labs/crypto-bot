"""Stdlib-only LLM client (OpenAI-compatible chat completions).

Reused by LLMStrategy and AgentDesk LLMDecisionCore.
Config via env: LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, ENABLE_LLM.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import logging

log = logging.getLogger(__name__)


def _load_dotenv(path: str | None = None) -> None:
    """Minimal .env loader - reads KEY=VAL lines, sets os.environ if not already set."""
    if path is None:
        # try common locations
        for candidate in (".env", os.path.join(os.path.dirname(__file__), "..", ".env")):
            if os.path.isfile(candidate):
                path = candidate
                break
        else:
            return  # no .env found
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if key and not os.environ.get(key):
                    os.environ[key] = val
    except Exception:
        pass


def is_enabled() -> bool:
    _load_dotenv()
    return os.getenv("ENABLE_LLM", "0") == "1"


def api_key() -> str:
    _load_dotenv()
    return os.getenv("LLM_API_KEY", "")


def base_url() -> str:
    _load_dotenv()
    return os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")


def model() -> str:
    _load_dotenv()
    return os.getenv("LLM_MODEL", "gpt-3.5-turbo")


def chat(prompt: str, max_tokens: int = 256, temperature: float = 0.3) -> str:
    """POST prompt to LLM chat endpoint. Returns raw lowercase content."""
    if not is_enabled():
        raise RuntimeError("LLM disabled (ENABLE_LLM=0)")
    key = api_key()
    if not key:
        raise ValueError("LLM_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model(),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        base_url().rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            # take first JSON object (handle trailing content from some models)
            idx = raw.rfind("}")
            if idx > 0:
                raw = raw[:idx+1]
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"].strip().lower()
    except urllib.error.HTTPError as e:
        log.error("LLM HTTP error %s: %s", e.code, e.read().decode())
        raise
    except Exception:
        log.exception("LLM request failed")
        raise
