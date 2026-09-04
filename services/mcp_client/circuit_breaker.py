"""NIYAM Circuit Breaker for Razorpay MCP Integration
Implements fail-closed resilience pattern with integrated chaos engineering toggle for live demos.
"""
import time
from enum import Enum
from typing import Callable, Any, Optional


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal healthy operation
    OPEN = "OPEN"          # Outage tripped, fail closed immediately
    HALF_OPEN = "HALF_OPEN"# Probe state testing upstream recovery


class CircuitBreakerOpenException(Exception):
    """Raised when request is rejected due to open circuit breaker."""
    pass


class CircuitBreaker:
    """Protects against cascading failures and upstream payment outages.
    
    Guarantees:
    - Never fail-open: If Razorpay is degraded, fail closed and block payment.
    - Chaos Toggle: Allows live demonstration of upstream outage handling in 1 click.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
        name: str = "Razorpay-MCP-CircuitBreaker"
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.last_state_change: float = time.time()
        self.last_failure_time: Optional[float] = None
        
        # Live demo chaos mode: forces circuit breaker into OPEN state
        self.chaos_mode: bool = False

    def set_chaos_mode(self, enabled: bool) -> None:
        """Enable or disable simulated upstream outage for live judging demos."""
        self.chaos_mode = enabled
        if enabled:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        else:
            self.state = CircuitState.CLOSED
            self.failure_count = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function protected by the circuit breaker."""
        # 1. Immediate check for simulated chaos
        if self.chaos_mode:
            raise CircuitBreakerOpenException(
                f"[{self.name}] Upstream Razorpay outage simulated (Chaos Mode Active). Fail-closed triggered."
            )

        # 2. Check state
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenException(
                    f"[{self.name}] Circuit is OPEN. Upstream Razorpay unavailable. Fail-closed triggered."
                )

        # 3. Attempt execution
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "chaos_mode": self.chaos_mode,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time
        }
