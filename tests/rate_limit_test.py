from __future__ import annotations

import time

import limits
import pytest

from multifutures import multithread
from multifutures import RateLimit
from multifutures import wait


def return_one(rate_limit: RateLimit):
    while rate_limit.reached("identifier"):
        wait()
    return 1


@pytest.mark.parametrize("jitter", [True, False])
def test_wait(jitter):
    wait(0.00001, jitter=jitter)


def test_rate_limit_default():
    rate_limit = RateLimit(strategy=None)
    assert str(rate_limit.rate_limit) == "5 per 1 second"
    assert isinstance(rate_limit.strategy, limits.strategies.MovingWindowRateLimiter)
    assert isinstance(rate_limit.strategy.storage, limits.storage.MemoryStorage)


def test_ratelimit() -> None:
    limit = 10
    rate_limit = RateLimit(rate_limit=limits.parse(f"{limit}/second"))

    # When doing fewer `repetitions` than `limit` runtime should be practically 0
    repetitions = limit - 1
    t1 = time.time()
    number_of_executions = sum(return_one(rate_limit=rate_limit) for _ in range(repetitions))
    t2 = time.time()
    duration = t2 - t1
    assert number_of_executions == repetitions
    assert duration == pytest.approx(0, abs=0.1)

    # When doing more `repetitions` than `limit` runtime should be 1 second + something really small
    repetitions = limit + 1
    t1 = time.time()
    number_of_executions = sum(return_one(rate_limit=rate_limit) for _ in range(repetitions))
    t2 = time.time()
    assert number_of_executions == repetitions
    assert t2 - t1 > 1
    assert t2 - t1 == pytest.approx(1, rel=0.25)


def test_ratelimit_multithread() -> None:
    # Define a function with a rate limit of N calls / second and call it N+1 times
    # Then check that the duration of all the calls was ≰ 1 second
    limit = 5
    rate_limit = RateLimit(rate_limit=limits.parse(f"{limit}/second"))

    # When doing fewer `repetitions` than `limit` runtime should be practically 0
    repetitions = limit - 1
    t1 = time.time()
    results = multithread(return_one, [{"rate_limit": rate_limit} for _ in range(repetitions)])
    assert all(r.exception is None for r in results)
    number_of_executions = sum(r.result for r in results)
    t2 = time.time()
    duration = t2 - t1
    assert number_of_executions == repetitions
    assert duration == pytest.approx(0, abs=0.1)

    # When doing more `repetitions` than `limit` runtime should be 1 second + something really small
    repetitions = limit + 1
    t1 = time.time()
    results = multithread(return_one, [{"rate_limit": rate_limit} for _ in range(repetitions)])
    assert all(r.exception is None for r in results)
    number_of_executions = sum(r.result for r in results)
    t2 = time.time()
    duration = t2 - t1
    assert number_of_executions == repetitions
    assert t2 - t1 > 1
    assert t2 - t1 == pytest.approx(1, rel=0.25)


# def test_RateLimit_multiprocess() -> None:
#     # Define a function with a rate limit of N calls / second and call it N+1 times
#     # Then check that the duration of all the calls was ≰ 1 second
#     limit = 5
#     rate_limit = RateLimit(rate_limit=limits.parse(f"{limit}/second"))
#
#     # When doing fewer `repetitions` than `limit` runtime should be practically 0
#     repetitions = limit - 1
#     t1 = time.time()
#     results = multiprocess(return_one, [dict(rate_limit=rate_limit) for i in range(repetitions)])
#     assert all([r.exception is None for r in results])
#     number_of_executions = sum(r.result for r in results)
#     t2 = time.time()
#     duration = t2 - t1
#     assert number_of_executions == repetitions
#     assert duration == pytest.approx(0, abs=0.1)
#
#     # When doing more `repetitions` than `limit` runtime should be 1 second + something really small
#     repetitions = limit + 1
#     t1 = time.time()
#     results = multithread(return_one, [dict(rate_limit=rate_limit) for i in range(repetitions)])
#     assert all([r.exception is None for r in results])
#     number_of_executions = sum(r.result for r in results)
#     t2 = time.time()
#     duration = t2 - t1
#     assert number_of_executions == repetitions
#     assert t2 - t1 > 1
#     assert t2 - t1 == pytest.approx(1, rel=0.1)
