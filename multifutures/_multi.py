from __future__ import annotations

import dataclasses
import logging
import multiprocessing
import typing as T
import warnings
from collections import abc
from concurrent.futures import as_completed
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import exceptiongroup
import tqdm.auto

from ._common import ExecutorProtocol
from ._common import ProgressBarProtocol


logger = logging.getLogger(__name__)

if T.TYPE_CHECKING:
    from typing_extensions import reveal_type


_DEPRECATION_PROGRESS_BAR_IS_NONE = "multifutures: Using `progress_bar=None` is deprecated and will be removed in a future release. Replace it with `progress_bar=True`"  # noqa: E501: Line too long


def _resolve_multiprocess_executor(executor: ExecutorProtocol | None, max_workers: int | None) -> ExecutorProtocol:
    if executor and max_workers:
        raise ValueError("Can't specify both `executor` and `max_workers`. Choose one or the other")
    elif executor:
        _executor = executor
    else:
        try:
            import loky

            _executor = loky.get_reusable_executor(max_workers=max_workers)
        except ImportError:
            ctx = multiprocessing.get_context("spawn")
            _executor = ProcessPoolExecutor(mp_context=ctx, max_workers=max_workers)
    return _executor


def _resolve_multithreading_executor(executor: ExecutorProtocol | None, max_workers: int | None) -> ExecutorProtocol:
    _executor: ExecutorProtocol
    if executor and max_workers:
        raise ValueError("Can't specify both `executor` and `max_workers`. Choose one or the other")
    elif executor:
        _executor = executor
    else:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def _resolve_progress_bar(
    progress_bar: ProgressBarProtocol | bool | None,
    func_kwargs: abc.Collection[dict[str, T.Any]],
) -> ProgressBarProtocol:
    if progress_bar is None:
        warnings.warn(
            _DEPRECATION_PROGRESS_BAR_IS_NONE,
            DeprecationWarning,
            stacklevel=2,
        )
        progress_bar = True
    if isinstance(progress_bar, tqdm.tqdm):
        _progress_bar = progress_bar
    elif progress_bar is False:
        _progress_bar = tqdm.auto.tqdm(total=len(func_kwargs), disable=True)
    else:
        _progress_bar = tqdm.auto.tqdm(total=len(func_kwargs))
    return _progress_bar


@dataclasses.dataclass
class FutureResult:
    """
    A [dataclass][dataclasses.dataclass] that holds the results of a function executed via
    [multiprocess][multifutures.multiprocess] or [multithread][multifutures.multithread].

    Note:
        Not meant to be instantiated directly.

    For example in the following snippet, `results` is going to be a list of `FutureResult` objects

        >>> func = lambda it: sum(it)
        >>> func_kwargs = [dict(it=range(i)) for i in range(5)]
        >>> results = multiprocess(func, func_kwargs)
        >>> results
        [FutureResult(exception=None, kwargs={'iterable': range(0, 0)}, result=0),
         FutureResult(exception=None, kwargs={'iterable': range(0, 1)}, result=0),
         FutureResult(exception=None, kwargs={'iterable': range(0, 2)}, result=1),
         FutureResult(exception=None, kwargs={'iterable': range(0, 3)}, result=3),
         FutureResult(exception=None, kwargs={'iterable': range(0, 4)}, result=6)]

    Parameters:
        exception:
            Will be `None` unless an `Exception` has been raised during the function execution
            in which case the attribute will contain the exception object.
        kwargs:
            May contain the keyword arguments that were used in the function call.
            If the objects passed as `kwargs` are too big (RAM-wise), e.g. big dataframes,
            you can omit them by passing `include_kwargs=False` in
            [multiprocess][multifutures.multiprocess]/[multithread][multifutures.multithread]".
        result:
            Will contain the function's output. If an `Exception` has been raised, then it will be `None`.
    """

    exception: Exception | None
    kwargs: dict[str, T.Any] | None
    result: T.Any


def check_results(results: list[FutureResult]) -> None:
    """
    Raises an [ExceptionGroup][ExceptionGroup] if any of the `results` contains an exception.

    Raises:
        ExceptionGroup: An exception group containing all the individual exceptions.
            Support for Python < 3.11 is provided via the [exceptiongroup](exceptiongroup) package.
            Check [here](https://github.com/agronholm/exceptiongroup#catching-exceptions) for more info.
    """

    exceptions = [r.exception for r in results if r.exception is not None]
    if exceptions:
        exception_group = exceptiongroup.ExceptionGroup("There were exceptions", exceptions)
        raise exception_group


def _multi(
    *,
    executor: ExecutorProtocol,
    func: abc.Callable[..., T.Any],
    func_kwargs: abc.Collection[dict[str, T.Any]],
    include_kwargs: bool,
    progress_bar: ProgressBarProtocol,
    check: bool,
) -> list[FutureResult]:
    with progress_bar:
        with executor as xctr:
            futures_to_kwargs = {xctr.submit(func, **kwargs): kwargs for kwargs in func_kwargs}
            results = []
            for future in as_completed(futures_to_kwargs):
                func_result = None
                exception = None
                result_kwargs: dict[str, T.Any] | None = None
                if include_kwargs:
                    result_kwargs = futures_to_kwargs[future]
                try:
                    func_result = future.result()
                except Exception as exc:
                    exception = exc
                finally:
                    results.append(FutureResult(result=func_result, exception=exception, kwargs=result_kwargs))
                    progress_bar.update(1)
    if check:
        check_results(results)
    return results


def multithread(
    func: abc.Callable[..., T.Any],
    func_kwargs: abc.Collection[dict[str, T.Any]],
    *,
    max_workers: int | None = None,
    executor: ExecutorProtocol | None = None,
    check: bool = False,
    include_kwargs: bool = True,
    progress_bar: ProgressBarProtocol | bool | None = True,
) -> list[FutureResult]:
    """
    Call `func` over all the items of `func_kwargs` using a multithreading Pool
    and return a list of [FutureResult][multifutures.FutureResult] objects.

    The pool by default is an instance of [ThreadPoolExecutor][concurrent.futures.ThreadPoolExecutor].
    The pool size can be limited with `max_workers`. If more control is needed,
    then the caller should directly pass a [ThreadPoolExecutor][concurrent.futures.ThreadPoolExecutor]
    instance to `executor`. For example:

    ``` python
    # Customize executor
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="AAA"
    )
    multithread(func, func_kwargs, executor=executor)
    ```

    The progress of the pool's workers can be monitored by using a
    [tqdm](https://tqdm.github.io/) based progress bar.
    The progress bar is displayed by default.
    Disabling the progress bar is possible by passing `progress_bar=False`.
    Further customizing of the progress bar should be done by creating a `tqdm.tqdm`
    instance and passing it as an argument to `progress_bar`. For example:

    ``` python
    # Run without a progress bar
    results = multithread(func, func_kwargs, progress_bar=False)

    # Run with a rich based progress bar
    rich_based_progress_bar = tqdm.rich.tqdm(func_kwargs)
    results = multithread(func, func_kwargs, progress_bar=rich_based_progress_bar)
    ```

    Arguments:
        func: The function that will be scheduled for execution via multithreading.
        func_kwargs: A Collection of dictionaries that will be used for the calls of `func`.
        executor: The multithreading [Executor][concurrent.futures.Executor] instance that we want to use.
            Defaults to the standard library's [ThreadPoolExecutor][concurrent.futures.ThreadPoolExecutor].
        check: If `True` then if any of the `func` calls raised an exception, an
            [ExceptionGroup][ExceptionGroup] containing all the exceptions will be raised.
        include_kwargs: A boolean flag indicating whether the keyword arguments of the
            functions will be present in the [FurureResult][multifutures.FutureResult]
            object. Setting this to `False` is useful for keeping memory usage down when
            the input are "heavy" objects like [xarray.Dataset][xarray.Dataset] etc.
        progress_bar: An instance of a progress bar implementing the `tqdm` API. Defaults to
            `tqdm.auto.tqdm`.

    Returns:
        A list of [FutureResult][multifutures.FutureResult] objects. Each object
            will contain the output of `func(**func_kwarg)` or an `Exception`.

    Raises:
        exceptiongroup.ExceptionGroup: If any of the function calls raises an exception and `check` is True.

    """
    progress_bar = _resolve_progress_bar(progress_bar, func_kwargs)
    executor = _resolve_multithreading_executor(executor=executor, max_workers=max_workers)
    results = _multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        include_kwargs=include_kwargs,
        progress_bar=progress_bar,
        check=check,
    )
    return results


def multiprocess(
    func: abc.Callable[..., T.Any],
    func_kwargs: abc.Collection[dict[str, T.Any]],
    *,
    max_workers: int | None = None,
    executor: ExecutorProtocol | None = None,
    check: bool = False,
    include_kwargs: bool = True,
    progress_bar: ProgressBarProtocol | bool | None = True,
) -> list[FutureResult]:
    """
    Call `func` over all the items of `func_kwargs` using a multiprocessing Pool
    and return a list of [FutureResult][multifutures.FutureResult] objects.

    The pool by default is an instance of [loky.ProcessPoolExecutor](https://loky.readthedocs.io/en/stable/),
    or, if `loky` is not installed, an instance of
    [concurrent.futures.ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor]
    using the `spawn` multiprocessing context.

    The pool size can be limited with `max_workers`. If more control is needed, e.g. to use a different
    multiprocessing context, then the caller should directly pass a `ProcessPoolExecutor`
    instance to `executor`. For example:

    ``` python
    # Customize executor
    mp_context = multiprocessing.get_context("forkserver")
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=mp_context)
    multiprocess(func, func_kwargs, executor=executor)
    ```

    The progress of the pool's workers can be monitored by using a
    [tqdm](https://tqdm.github.io/) based progress bar.
    The progress bar is displayed by default.
    Disabling the progress bar is possible by passing `progress_bar=False`.
    Further customizing of the progress bar should be done by creating a `tqdm.tqdm`
    instance and passing it as an argument to `progress_bar`. For example:

    ``` python
    # Run without a progress bar
    results = multithread(func, func_kwargs, progress_bar=False)

    # Run with a rich based progress bar
    rich_based_progress_bar = tqdm.rich.tqdm(func_kwargs)
    results = multithread(func, func_kwargs, progress_bar=rich_based_progress_bar)
    ```

    Arguments:
        func: The function that will be scheduled for execution via multiprocessing.
        func_kwargs: A Collection of dictionaries that will be used for the calls of `func`.
        executor: A multiprocessing [Executor][concurrent.futures.Executor] instance.
            Defaults to [loky.get_reusable_executor()][loky.get_reusable_executor],
            which uses the `loky` multiprocessing context
            ([more info](https://loky.readthedocs.io/en/stable/API.html#processes-start-methods-in-loky)).
            If [loky][loky] is not installed, it defaults to Standard Library's
            [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] with the `spawn` multiprocessing
            start method ([more info](https://docs.python.org/3/library/multiprocessing.html#multiprocessing-start-methods))
        check: If `True` then if any of the `func` calls raised an exception, an
            [ExceptionGroup][ExceptionGroup] containing all the exceptions will be raised.
        include_kwargs: A boolean flag indicating whether the keyword arguments of the
            functions will be present in the [FurureResult][multifutures.FutureResult]
            object. Setting this to `False` is useful for keeping memory usage down when
            the input are "heavy" objects like [xarray.Dataset][xarray.Dataset] etc.
        progress_bar: An instance of a progress bar implementing the `tqdm` API. Defaults to
            `tqdm.auto.tqdm`.

    Returns:
        A list of [FutureResult][multifutures.FutureResult] objects. Each object
            will contain the output of `func(**func_kwargs[i])` or an `Exception`.

    Raises:
        exceptiongroup.ExceptionGroup: If any of the function calls raises an exception and `check` is True.

    """
    progress_bar = _resolve_progress_bar(progress_bar, func_kwargs)
    executor = _resolve_multiprocess_executor(executor=executor, max_workers=max_workers)
    results = _multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        include_kwargs=include_kwargs,
        progress_bar=progress_bar,
        check=check,
    )
    return results
