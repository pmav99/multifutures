from __future__ import annotations

import random
import time
import typing as T

if T.TYPE_CHECKING:
    import limits

FIVE_PER_SECOND = "5/second"


def wait(wait_time: float = 0.1, *, jitter: bool = True) -> None:
    """Wait for `wait_time` + some random `jitter`"""
    if jitter:
        # Set jitter to be <= 1% of wait_time
        jitter_time = random.random() / (1 / wait_time * 100)  # noqa: S311 - suspicious-non-cryptographic-random-usage
    else:
        jitter_time = 0
    time.sleep(wait_time + jitter_time)


class RateLimit:
    """
    A wrapper around the [limits](https://limits.readthedocs.io/en/stable/index.html) library.
    It defaults to using the [Moving Window Strategy][limits.strategies.MovingWindowRateLimiter]
    on the [Memory Storage][limits.storage.MemoryStorage].

    Warning:
        The default strategy only works with multi-threading, not multi-processing.
        If you want to use it with multiprocessing you need to use a different storage backend (e.g. redis).

    ## Usage

        rate_limit = RateLimit()

        while rate_limit.reached():
            wait()

    Arguments:
        rate_limit: The rate limit. An instance of [limits.parse][limits.parse].
            Defaults to 5 requests per seconds.
        strategy: The strategy to use. Defaults to a Moving Window using the Memory Storage.

    """

    def __init__(
        self,
        rate_limit: limits.RateLimitItem | None = None,
        strategy: limits.strategies.RateLimiter | None = None,
    ) -> None:
        import limits

        self.rate_limit = rate_limit or limits.parse("5/second")
        if strategy is None:
            storage = limits.storage.MemoryStorage()
            strategy = limits.strategies.MovingWindowRateLimiter(storage)
        self.strategy = strategy

    def reached(self, identifier: str = "") -> bool:
        """
        Returns `True` if the rate limit has been reached, `False` otherwise.

        `RateLimit` instances can be reused in different contexts.
        To do so a unique identifier per-context must be provided.

        Arguments:
            identifier: The identifier allows you to reuse the `RateLimit` instance in different contexts.

        """
        return not self.strategy.hit(
            self.rate_limit,
            identifier,
        )
