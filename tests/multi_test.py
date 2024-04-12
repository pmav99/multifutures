from __future__ import annotations

import concurrent.futures
import multiprocessing
import sys
from unittest.mock import patch

import exceptiongroup
import loky
import pytest
import tqdm.auto

from multifutures import _multi as multi

CONCURRENCY_FUNCS = pytest.mark.parametrize("concurrency_func", [multi.multithread, multi.multiprocess])
MP_CONTEXTS = ["fork", "spawn", "forkserver", "loky", "loky_init_main"]


def raise_zero_division_error(**kwargs) -> None:  # noqa: ARG001: Unused function argument
    raise ZeroDivisionError()


def return_one(**kwargs) -> float:  # noqa: ARG001: Unused function argument
    return 1


@pytest.mark.parametrize("context", MP_CONTEXTS)
@pytest.mark.parametrize(
    "executor_class",
    [
        pytest.param(loky.get_reusable_executor, id="loky.get_reusable_executor"),
        pytest.param(loky.ProcessPoolExecutor, id="loky.ProcessPoolExecutor"),
        pytest.param(concurrent.futures.ProcessPoolExecutor, id="concurrent.futures.ProcessPoolExecutor"),
    ],
)
def test_multiprocess_pass_executor_as_argument(executor_class, context):
    if executor_class == loky.get_reusable_executor and context == "fork":
        pytest.skip("Reusable executor doesn't work with 'fork' context")

    # loky uses a different argument name for mp_context
    context = multiprocessing.get_context(context)
    if executor_class == concurrent.futures.ProcessPoolExecutor:
        executor = executor_class(mp_context=context)
    else:
        executor = executor_class(context=context)

    no_func_calls = 2
    results = multi.multiprocess(
        func=return_one,
        func_kwargs=[{"number": 1}] * no_func_calls,
        executor=executor,
    )
    assert sum(result.result for result in results) == no_func_calls


def test_multithread_pass_executor_as_argument():
    executor = concurrent.futures.ThreadPoolExecutor()
    no_func_calls = 2
    results = multi.multithread(
        func=return_one,
        func_kwargs=[{"number": 1}] * no_func_calls,
        executor=executor,
    )
    assert sum(result.result for result in results) == no_func_calls


@CONCURRENCY_FUNCS
@pytest.mark.parametrize("max_workers", [None, 2])
def test_concurrency_functions_pass_max_workers_as_argument(concurrency_func, max_workers) -> None:
    kwargs = {"arg": 111}
    no_func_calls = 2
    results = concurrency_func(func=return_one, func_kwargs=[kwargs] * no_func_calls, max_workers=max_workers)
    assert sum(result.result for result in results) == no_func_calls


@CONCURRENCY_FUNCS
def test_concurrency_functions_returns_futureresult(concurrency_func) -> None:
    no_tests = 2
    results = concurrency_func(
        func=return_one,
        func_kwargs=[{"number": 42}] * no_tests,
    )
    assert len(results) == no_tests
    for result in results:
        assert isinstance(result, multi.FutureResult)
        assert result.result == 1
        assert result.exception is None


@CONCURRENCY_FUNCS
def test_concurrency_functions_returns_futureresult_even_when_exceptions_are_raised(concurrency_func) -> None:
    no_tests = 2
    results = concurrency_func(
        func=raise_zero_division_error,
        func_kwargs=[{}] * no_tests,
    )
    assert len(results) == no_tests
    for result in results:
        assert isinstance(result, multi.FutureResult)
        assert result.result is None
        assert isinstance(result.exception, ZeroDivisionError)


@CONCURRENCY_FUNCS
def test_check(concurrency_func) -> None:
    no_tests = 2
    with pytest.raises(exceptiongroup.ExceptionGroup) as exc:
        concurrency_func(
            func=raise_zero_division_error,
            func_kwargs=[{}] * no_tests,
            check=True,
        )
    assert "There were exceptions" in str(exc)
    assert len(exc.value.exceptions) == no_tests
    assert all(isinstance(sub_exc, ZeroDivisionError) for sub_exc in exc.value.exceptions)


@CONCURRENCY_FUNCS
def test_check_results(concurrency_func) -> None:
    no_tests = 2
    results = concurrency_func(
        func=raise_zero_division_error,
        func_kwargs=[{}] * no_tests,
        check=False,
    )
    with pytest.raises(exceptiongroup.ExceptionGroup) as exc:
        multi.check_results(results)
    assert "There were exceptions" in str(exc)
    assert len(exc.value.exceptions) == no_tests
    assert all(isinstance(sub_exc, ZeroDivisionError) for sub_exc in exc.value.exceptions)


@CONCURRENCY_FUNCS
@pytest.mark.parametrize("include_kwargs", [True, False])
def test_concurrency_functions_include_kwargs(concurrency_func, include_kwargs) -> None:
    kwargs = {"arg": 111}
    no_tests = 2
    results = concurrency_func(
        func=return_one,
        func_kwargs=[kwargs] * no_tests,
        include_kwargs=include_kwargs,
    )
    if include_kwargs:
        assert all(result.kwargs == kwargs for result in results)
    else:
        assert all(result.kwargs is None for result in results)


@CONCURRENCY_FUNCS
def test_concurrency_functions_use_progress_bar(capsys, concurrency_func) -> None:
    no_tests = 2
    kwargs = [{"arg": 111}] * no_tests
    results = concurrency_func(
        func=return_one,
        func_kwargs=kwargs,
    )
    captured = capsys.readouterr()
    assert sum(result.result for result in results) == no_tests
    assert captured.out == ""
    assert captured.err != ""
    assert "it/s" in captured.err


@CONCURRENCY_FUNCS
def test_concurrency_functions_disable_progress_bar(capsys, concurrency_func) -> None:
    no_tests = 2
    kwargs = [{"arg": 111}] * no_tests
    results = concurrency_func(
        func=return_one,
        func_kwargs=kwargs,
        progress_bar=False,
    )
    captured = capsys.readouterr()
    assert sum(result.result for result in results) == no_tests
    assert captured.out == ""
    assert captured.err == ""


@CONCURRENCY_FUNCS
def test_concurrency_functions_custom_progress_bar(concurrency_func) -> None:
    no_tests = 2
    kwargs = [{"arg": 111}] * no_tests
    progress_bar = tqdm.auto.tqdm(kwargs, disable=True)
    results = concurrency_func(
        func=return_one,
        func_kwargs=kwargs,
        progress_bar=progress_bar,
    )
    assert sum(result.result for result in results) == no_tests
    assert progress_bar.total == no_tests


def test_resolve_multiprocess_executor_default_with_loky():
    executor = multi._resolve_multiprocess_executor(None, None)
    assert isinstance(executor, loky.ProcessPoolExecutor)


def test_resolve_multiprocess_executor_default_without_loky():
    with patch.dict(sys.modules, {"loky": None}):
        executor = multi._resolve_multiprocess_executor(None, None)
        assert isinstance(executor, concurrent.futures.ProcessPoolExecutor)


@pytest.mark.parametrize("max_workers", [1, 2, 4])
def test_resolve_multiprocess_executor_with_max_workers(max_workers):
    executor = multi._resolve_multiprocess_executor(None, max_workers=max_workers)
    assert executor._max_workers == max_workers


@pytest.mark.parametrize("max_workers", [1, 2, 4])
def test_resolve_multithread_executor_with_max_workers(max_workers):
    executor = multi._resolve_multithreading_executor(None, max_workers=max_workers)
    assert executor._max_workers == max_workers


@CONCURRENCY_FUNCS
def test_specifying_both_executor_and_max_workers_raises(concurrency_func):
    with pytest.raises(ValueError) as exc:
        concurrency_func(
            func=return_one,
            func_kwargs=[{}],
            executor=concurrent.futures.ProcessPoolExecutor(),
            max_workers=5,
        )
    assert "Can't specify both `executor` and `max_workers`. Choose one or the other" in exc.exconly()


@CONCURRENCY_FUNCS
def test_concurrency_functions_progress_bar_is_none_deprecation_warning(concurrency_func):
    with pytest.deprecated_call(match=multi._DEPRECATION_PROGRESS_BAR_IS_NONE):
        concurrency_func(
            func=return_one,
            func_kwargs=[{}],
            progress_bar=None,
        )
