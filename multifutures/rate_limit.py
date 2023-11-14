from __future__ import annotations

import random
import time

import limits


def wait(wait_time: float = 0.1, *, jitter: bool = True) -> None:
    """Wait for `wait_time` + some random `jitter`"""
    if jitter:
        # Set jitter to be <= 1% of wait_time
        jitter_time = random.random() / (1 / wait_time * 100)  # noqa: S311 - suspicious-non-cryptographic-random-usage
    else:
        jitter_time = 0
    time.sleep(wait_time + jitter_time)


class RateLimit:
    def __init__(
        self,
        rate_limit: limits.RateLimitItem | None = None,
        storage: type[limits.storage.Storage] = limits.storage.MemoryStorage,
        strategy: type[limits.strategies.RateLimiter] = limits.strategies.MovingWindowRateLimiter,
    ) -> None:
        self.rate_limit = rate_limit or limits.parse("5/second")
        self.storage = storage()
        self.strategy = strategy(self.storage)

    def reached(self, identifier: str) -> bool:
        return not self.strategy.hit(
            self.rate_limit,
            identifier,
        )
