"""
Helpers for multi processing/threading
"""
from __future__ import annotations

import logging
import os
import sys
import typing as T
from collections.abc import Callable
from concurrent.futures import as_completed
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import pydantic
import tqdm.auto

# from loky import ProcessPoolExecutor  # FTR, `loky.ProcessPoolExecutor` is more robust WRT pickling big objects


logger = logging.getLogger(__name__)


# https://docs.python.org/3/library/os.html#os.cpu_count
if sys.platform == "darwin":
    MAX_AVAILABLE_PROCESSES = os.cpu_count() or 1
else:
    try:
        MAX_AVAILABLE_PROCESSES = len(os.sched_getaffinity(0))
    except AttributeError:  # pragma: no cover
        MAX_AVAILABLE_PROCESSES = os.cpu_count() or 1  # os.cpu_count() may return None  # pragma: no cover


class FutureResult(pydantic.BaseModel):
    exception: T.Union[Exception, None] = None  # noqa: UP007 - Use X | Y for type annotations
    kwargs: T.Union[dict[str, T.Any], None] = None  # noqa: UP007 - Use X | Y for type annotations
    result: T.Any = None

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


def check_results(results: list[FutureResult]) -> None:
    failures = [str(r) for r in results if r.exception is not None]
    if failures:
        str_failures = "\n".join(failures)
        raise ValueError(f"There were failures:\n{str_failures}")


def multi(
    *,
    executor: type[ProcessPoolExecutor] | type[ThreadPoolExecutor],
    func: Callable[..., T.Any],
    func_kwargs: list[dict[str, T.Any]],
    n_workers: int,
    initializer: Callable[..., T.Any] | None,
    include_kwargs: bool,
    disable_progress_bar: bool,
    check: bool,
) -> list[FutureResult]:
    with tqdm.auto.tqdm(total=len(func_kwargs), disable=disable_progress_bar) as progress_bar:
        with executor(max_workers=n_workers, initializer=initializer) as xctr:
            futures_to_kwargs = {xctr.submit(func, **kwargs): kwargs for kwargs in func_kwargs}
            results = []
            for future in as_completed(futures_to_kwargs):
                result_kwargs: dict[str, T.Any] | None = futures_to_kwargs[future]
                try:
                    func_result = future.result()
                except Exception as exc:
                    if not include_kwargs:
                        result_kwargs = None
                    results.append(FutureResult(exception=exc, kwargs=result_kwargs))
                else:
                    if not include_kwargs:
                        result_kwargs = None
                    results.append(FutureResult(result=func_result, kwargs=result_kwargs))
                finally:
                    progress_bar.update(1)
    if check:
        check_results(results)

    return results


def multithread(
    func: Callable[..., T.Any],
    func_kwargs: list[dict[str, T.Any]],
    n_workers: int = max(1, MAX_AVAILABLE_PROCESSES - 1),
    *,
    include_kwargs: bool = True,
    executor: type[ThreadPoolExecutor] = ThreadPoolExecutor,
    initializer: Callable[..., T.Any] | None = None,
    disable_progress_bar: bool = False,
    check: bool = False,
) -> list[FutureResult]:
    results = multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        n_workers=n_workers,
        include_kwargs=include_kwargs,
        initializer=initializer,
        disable_progress_bar=disable_progress_bar,
        check=check,
    )
    return results


def multiprocess(
    func: Callable[..., T.Any],
    func_kwargs: list[dict[str, T.Any]],
    n_workers: int = max(1, MAX_AVAILABLE_PROCESSES - 1),
    *,
    include_kwargs: bool = True,
    executor: type[ProcessPoolExecutor] = ProcessPoolExecutor,
    initializer: Callable[..., T.Any] | None = None,
    disable_progress_bar: bool = False,
    check: bool = False,
) -> list[FutureResult]:
    if n_workers > MAX_AVAILABLE_PROCESSES:
        msg = f"The maximum available processes are {MAX_AVAILABLE_PROCESSES}, not: {n_workers}"
        raise ValueError(msg)
    results = multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        n_workers=n_workers,
        include_kwargs=include_kwargs,
        initializer=initializer,
        disable_progress_bar=disable_progress_bar,
        check=check,
    )
    return results
