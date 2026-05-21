import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

import redis.asyncio as redis


class RateLimitStrategy(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RateLimitConfig:
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    requests_per_second: int = 100
    requests_per_minute: int = 1000
    requests_per_hour: int = 10000
    burst_size: int = 200
    block_duration_seconds: int = 60


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    half_open_calls: int = 0


class TokenBucketRateLimiter:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def reset(self):
        async with self._lock:
            self.tokens = self.capacity
            self.last_update = time.monotonic()


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds

            self.requests[key] = [t for t in self.requests[key] if t > cutoff]

            if len(self.requests[key]) < self.max_requests:
                self.requests[key].append(now)
                return True
            return False

    async def get_remaining(self, key: str) -> int:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self.requests[key] = [t for t in self.requests[key] if t > cutoff]
            return max(0, self.max_requests - len(self.requests[key]))

    async def reset(self, key: str):
        async with self._lock:
            if key in self.requests:
                del self.requests[key]


class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        await self._check_state()

        if self.state.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e

    async def _check_state(self):
        async with self._lock:
            if self.state.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state.state = CircuitState.HALF_OPEN
                    self.state.half_open_calls = 0

    def _should_attempt_reset(self) -> bool:
        if self.state.last_failure_time is None:
            return True
        return time.monotonic() - self.state.last_failure_time >= self.config.timeout_seconds

    async def _on_success(self):
        async with self._lock:
            self.state.failure_count = 0

            if self.state.state == CircuitState.HALF_OPEN:
                self.state.success_count += 1
                self.state.half_open_calls += 1

                if self.state.success_count >= self.config.success_threshold:
                    self.state.state = CircuitState.CLOSED
                    self.state.success_count = 0

    async def _on_failure(self):
        async with self._lock:
            self.state.failure_count += 1
            self.state.last_failure_time = time.monotonic()

            if self.state.state == CircuitState.HALF_OPEN:
                self.state.state = CircuitState.OPEN
                self.state.half_open_calls = 0
            elif self.state.failure_count >= self.config.failure_threshold:
                self.state.state = CircuitState.OPEN

    async def get_state(self) -> Dict:
        return {
            "name": self.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count
        }

    async def reset(self):
        async with self._lock:
            self.state = CircuitBreakerState()


class CircuitBreakerOpenError(Exception):
    pass


class RateLimiter:
    def __init__(
        self,
        redis_client: redis.Redis = None,
        config: RateLimitConfig = None
    ):
        self.redis = redis_client
        self.config = config or RateLimitConfig()
        
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
        self.sliding_limiters: Dict[str, SlidingWindowRateLimiter] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        key: str,
        requests_per_second: int = None,
        requests_per_minute: int = None
    ) -> bool:
        if self.redis:
            return await self._check_redis_rate_limit(
                key,
                requests_per_second or self.config.requests_per_second,
                requests_per_minute or self.config.requests_per_minute
            )
        
        limiter = self.limiters.get(key)
        if not limiter:
            limiter = TokenBucketRateLimiter(
                rate=requests_per_second or self.config.requests_per_second,
                capacity=self.config.burst_size
            )
            self.limiters[key] = limiter
        
        return await limiter.acquire()

    async def _check_redis_rate_limit(
        self,
        key: str,
        rps: int,
        rpm: int
    ) -> bool:
        now = time.time()
        minute_key = f"ratelimit:minute:{key}"
        second_key = f"ratelimit:second:{key}"

        pipe = self.redis.pipeline()
        pipe.incr(second_key)
        pipe.expire(second_key, 1)
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        
        results = await pipe.execute()
        
        second_count = results[0]
        minute_count = results[2]
        
        if second_count > rps or minute_count > rpm:
            return False
        return True

    async def get_rate_limit_info(self, key: str) -> Dict:
        limiter = self.limiters.get(key)
        if not limiter:
            return {"allowed": True, "remaining": self.config.burst_size}
        
        remaining = int(limiter.tokens)
        return {
            "allowed": remaining > 0,
            "remaining": remaining,
            "capacity": limiter.capacity
        }

    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    async def circuit_breaker_call(
        self,
        name: str,
        func: Callable,
        *args,
        **kwargs
    ):
        cb = self.get_circuit_breaker(name)
        return await cb.call(func, *args, **kwargs)

    async def reset(self, key: str = None):
        if key:
            if key in self.limiters:
                await self.limiters[key].reset()
            if key in self.sliding_limiters:
                await self.sliding_limiters[key].reset(key)
        else:
            for limiter in self.limiters.values():
                await limiter.reset()
            self.limiters.clear()
            self.sliding_limiters.clear()


class RateLimitExceededError(Exception):
    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")