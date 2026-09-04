"""NIYAM Token-Bucket Rate Limiter
Defends merchant infrastructure against runaway AI agent loops and replay bursts.
Enforces per-agent rate limiting using an in-memory token-bucket algorithm.
"""
import time
from threading import Lock
from typing import Dict, Tuple, Optional


class TokenBucketRateLimiter:
    """Thread-safe token-bucket rate limiter per agent_id."""

    def __init__(self, capacity: int = 5, refill_rate_per_sec: float = 1.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self._lock = Lock()
        # agent_id -> (tokens_remaining, last_refill_timestamp)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def check_and_consume(self, agent_id: str, tokens: int = 1) -> Tuple[bool, float]:
        """Checks if agent has enough tokens and consumes them.
        Returns:
            (allowed: bool, retry_after_seconds: float)
        """
        now = time.time()
        with self._lock:
            if agent_id not in self._buckets:
                self._buckets[agent_id] = (float(self.capacity), now)

            current_tokens, last_refill = self._buckets[agent_id]
            
            # Calculate refilled tokens based on elapsed time
            elapsed = max(0.0, now - last_refill)
            current_tokens = min(float(self.capacity), current_tokens + (elapsed * self.refill_rate))
            
            if current_tokens >= tokens:
                # Consume tokens
                self._buckets[agent_id] = (current_tokens - tokens, now)
                return True, 0.0
            else:
                # Calculate wait time until at least 1 token is available
                needed = tokens - current_tokens
                retry_after = max(0.1, needed / self.refill_rate)
                self._buckets[agent_id] = (current_tokens, now)
                return False, retry_after

    def reset_agent(self, agent_id: str):
        """Resets token bucket for testing or administrative override."""
        with self._lock:
            if agent_id in self._buckets:
                del self._buckets[agent_id]
