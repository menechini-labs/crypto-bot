"""Per-provider rate limiter — in-memory token/request budget tracking."""

import time
import threading
import logging

log = logging.getLogger(__name__)

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and no budget available."""

class RateLimiter:
    """Simple sliding-window rate limiter (requests/min, tokens/min).

    Thread-safe. Uses monotonic time. Non-blocking acquire returns bool.
    """

    def __init__(self, max_requests_per_min: int = 10, max_tokens_per_min: int = 100000):
        self._max_req = max_requests_per_min
        self._max_tok = max_tokens_per_min
        self._lock = threading.Lock()
        # sliding window: list of (timestamp, tokens)
        self._window: list[tuple[float, int]] = []

    def acquire(self, tokens: int = 0, wait_ms: int = 500) -> bool:
        """Try to acquire a slot. Returns True if allowed, False if throttled.

        If False, caller should queue or defer. Never blocks beyond wait_ms.
        """
        deadline = time.monotonic() + wait_ms / 1000
        while True:
            with self._lock:
                self._prune()
                if len(self._window) < self._max_req:
                    tok_sum = sum(t for _, t in self._window)
                    if tok_sum + tokens <= self._max_tok:
                        self._window.append((time.monotonic(), tokens))
                        return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)  # 50ms backoff

    def record_tokens(self, count: int):
        """Record token usage without acquiring a slot (for tracking)."""
        with self._lock:
            self._prune()
            tok_sum = sum(t for _, t in self._window)
            if tok_sum + count <= self._max_tok:
                self._window.append((time.monotonic(), count))
            else:
                log.warning('Token budget exceeded: %d + %d > %d', tok_sum, count, self._max_tok)

    def _prune(self):
        """Remove entries older than 60s."""
        cutoff = time.monotonic() - 60
        self._window = [(ts, t) for ts, t in self._window if ts > cutoff]
