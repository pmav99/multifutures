from __future__ import annotations

import multiprocessing
import threading
import time

import pytest

from multifutures import multi


# Some help functions to test multithreading
def get_threadname(**kwargs) -> tuple[str, str]:
    del kwargs
    # We add a tiny amount of wait_time to make sure that all the threads are getting used.
    time.sleep(0.001)
    return threading.current_thread().name


def get_processname(**kwargs) -> tuple[str, str]:
    del kwargs
    # We add a tiny amount of wait_time to make sure that all the processes are getting used.
    time.sleep(0.05)
    return multiprocessing.current_process().name


def raise_zero_division_error(**kwargs) -> None:
    del kwargs
    raise ZeroDivisionError()


def return_one(number) -> float:
    del number
    return 1


# The actual tests
def test_multiprocess_raises_value_error_if_n_workers_higher_than_available_threads() -> None:
    with pytest.raises(ValueError) as exc:
        multi.multiprocess(func=lambda x: x, func_kwargs=[{"x": 1}] * 2, n_workers=1024)
    assert f"The maximum available processes are {multi.MAX_AVAILABLE_PROCESSES}, not: 1024" == str(exc.value)


@pytest.mark.parametrize(
    "concurrency_func",
    [multi.multithread, multi.multiprocess],
)
def test_concurrency_functions_returns_futureresult(concurrency_func) -> None:
    results = concurrency_func(
        func=return_one,
        func_kwargs=[{"number": n} for n in (1, 2, 3)],
    )
    for result in results:
        assert isinstance(result, multi.FutureResult)
        assert result.result == 1
        assert result.exception is None


@pytest.mark.parametrize(
    "concurrency_func",
    [multi.multithread, multi.multiprocess],
)
def test_concurrency_functions_returns_futureresult_even_when_exceptions_are_raised(
    concurrency_func,
) -> None:
    results = concurrency_func(
        func=raise_zero_division_error,
        func_kwargs=[{"number": n} for n in (1, 2, 3)],
    )
    for result in results:
        assert isinstance(result, multi.FutureResult)
        assert result.result is None
        assert isinstance(result.exception, ZeroDivisionError)


@pytest.mark.parametrize("n_workers", [1, 2, 4])
def test_multithread_pool_size(n_workers) -> None:
    if n_workers > multi.MAX_AVAILABLE_PROCESSES:  # = 4 and os.environ.get("CI", False):
        pytest.skip("Github actions only permits 2 concurrent threads")
    # Test that the number of the used threads is equal to the specified number of workers
    results = multi.multithread(
        func=get_threadname,
        func_kwargs=[{"arg": i} for i in range(4 * n_workers)],
        n_workers=n_workers,
    )
    thread_names = {result.result for result in results}
    assert len(thread_names) == n_workers


@pytest.mark.parametrize("n_workers", [1, 2, 4])
def test_multiprocess_pool_size(n_workers) -> None:
    if n_workers > multi.MAX_AVAILABLE_PROCESSES:  # = 4 and os.environ.get("CI", False):
        # if n_workers == 4 and os.environ.get("CI", False):
        pytest.skip("Github actions only permits 2 concurrent processes")
    # Test that the number of the used processes is equal to the specified number of workers
    results = multi.multiprocess(
        func=get_processname,
        func_kwargs=[{"arg": i} for i in range(4 * n_workers)],
        n_workers=n_workers,
    )
    process_names = {result.result for result in results}
    assert len(process_names) == n_workers


@pytest.mark.parametrize(
    "concurrency_func",
    [multi.multithread, multi.multiprocess],
)
def test_check(concurrency_func) -> None:
    func_kwargs = [{} for i in range(2)]
    with pytest.raises(ValueError) as exc:
        concurrency_func(
            func=raise_zero_division_error,
            func_kwargs=func_kwargs,
            n_workers=2,
            check=True,
        )
    assert "There were failures" in str(exc)
    assert len(str(exc.value).splitlines()) == 3  # 2 exceptions + header  # noqa: PLR2004: magic number comparison
