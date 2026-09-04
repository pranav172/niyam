"""NIYAM Idempotency Manager
Guarantees at-most-once financial execution for autonomous agent retries.
Prevents double debits, ghost orders, and duplicate charges.
"""
import time
from typing import Optional, Dict, Any
from threading import Lock


class IdempotencyManager:
    """Thread-safe TTL cache for purchase idempotency keys."""

    def __init__(self, ttl_seconds: float = 86400.0):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def _make_composite_key(self, idempotency_key: str, agent_id: str) -> str:
        return f"{agent_id}::{idempotency_key}"

    def check(self, idempotency_key: str, agent_id: str) -> Optional[Dict[str, Any]]:
        """Returns cached execution result if key exists and has not expired."""
        comp_key = self._make_composite_key(idempotency_key, agent_id)
        with self._lock:
            if comp_key in self._cache:
                entry = self._cache[comp_key]
                if time.time() - entry["created_at"] < self.ttl_seconds:
                    return entry["response"]
                else:
                    del self._cache[comp_key]
        return None

    def store(self, idempotency_key: str, agent_id: str, response_payload: Dict[str, Any]) -> None:
        """Stores execution result in idempotency cache."""
        comp_key = self._make_composite_key(idempotency_key, agent_id)
        with self._lock:
            self._cache[comp_key] = {
                "response": response_payload,
                "created_at": time.time()
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
