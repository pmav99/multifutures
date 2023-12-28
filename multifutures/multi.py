from __future__ import annotations

import concurrent.futures
import dataclasses
import logging
import multiprocessing
import typing as T
from collections import abc
from concurrent.futures import as_completed
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import exceptiongroup


logger = logging.getLogger(__name__)

if T.TYPE_CHECKING:
    import loky
    import tqdm.auto

_T = T.TypeVar("_T")


def _resolve_multiprocess_executor(
    executor: loky.ProcessPoolExecutor | concurrent.futures.ProcessPoolExecutor | None = None,
) -> loky.ProcessPoolExecutor | concurrent.futures.ProcessPoolExecutor:
    if executor is None:
        try:
            import loky

            executor = loky.get_reusable_executor()
        except ImportError:
            ctx = multiprocessing.get_context("spawn")
            executor = ProcessPoolExecutor(mp_context=ctx)
    return executor


def _resolve_progress_bar(
    progress_bar: tqdm.tqdm[_T] | None,
    func_kwargs: abc.Collection[dict[str, T.Any]],
) -> tqdm.tqdm[_T]:
    if progress_bar is None:
        import tqdm.auto

        progress_bar = tqdm.auto.tqdm(total=len(func_kwargs))  # type: ignore[assignment]
    return progress_bar  # type: ignore[return-value]


@dataclasses.dataclass
class FutureResult:
    """
    A [dataclass][dataclasses.dataclass] that holds the results of a function executed via
    [multiprocess][multifutures.multiprocess] or [multithread][multifutures.multithread].

    Note:
        Not meant to be instantiated directly.

    For example in the following snippet, results is going to be a list of `FutureResult` objects

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
    executor: ProcessPoolExecutor | ThreadPoolExecutor | loky.ProcessPoolExecutor,
    func: abc.Callable[..., T.Any],
    func_kwargs: abc.Collection[dict[str, T.Any]],
    include_kwargs: bool,
    progress_bar: tqdm.tqdm | None = None,  # type: ignore[type-arg]
    check: bool,
) -> list[FutureResult]:
    progress_bar = _resolve_progress_bar(progress_bar, func_kwargs)
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
    executor: ThreadPoolExecutor | None = None,
    check: bool = False,
    include_kwargs: bool = True,
    progress_bar: tqdm.tqdm | None = None,  # type: ignore[type-arg]
) -> list[FutureResult]:
    """
    Call `func` over all the items of `func_kwargs` using a multithreading Pool
    and return a list of [FutureResult][multifutures.FutureResult].

    Arguments:
        func: The function that will be scheduled for execution via multithreading.
        func_kwargs: A Collection of dictionaries that will be used for the calls of `func`.
        executor: The multithreading [Executor][concurrent.futures.Executor] instance that we want to use.
            Defaults to the standard library's [ThreadPoolExecutor][concurrent.futures.ThreadPoolExecutor].
        check: If `True` then if any of the `func` calls raised an exception, an
            [ExceptionGroup][ExceptionGroup] containing all the exceptions will be raised.
        include_kwargs: A boolean flag indicating whether the keyword arguments of the
            functions will be present in the [FurureResult][multifutures.FutureResult]
            object. Useful for keeping memory usage down when the input are objects like
            `xarray.Dataset` etc.
        progress_bar: An instance of a progress bar implementing the `tqdm` API. Defaults to
            `tqdm.auto.tqdm`. If you want to disable it you can do so by passing `disable=True`
            when creating the `progress_bar`.

                progress_bar = tqdm.auto.tqdm(func_kwargs, disable=True)
                results = multiprocess(func, func_kwargs, progress_bar=progress_bar)

    Returns:
        A list of [FutureResult][multifutures.FutureResult] objects. Each object
            will contain the output of `func(**func_kwarg)` or an `Exception`.

    Raises:
        exceptiongroup.ExceptionGroup: If any of the function calls raises an exception and `check` is True.

    """
    if executor is None:
        executor = ThreadPoolExecutor()
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
    executor: loky.ProcessPoolExecutor | ProcessPoolExecutor | None = None,
    check: bool = False,
    include_kwargs: bool = True,
    progress_bar: tqdm.tqdm | None = None,  # type: ignore[type-arg]
) -> list[FutureResult]:
    """
    Call `func` over all the items of `func_kwargs` using a multiprocessing Pool
    and return a list of [FutureResult][multifutures.FutureResult].

    Arguments:
        func: The function that will be scheduled for execution via multiprocessing.
        func_kwargs: A Collection of dictionaries that will be used for the calls of `func`.
        executor: The multiprocessing [Executor][concurrent.futures.Executor].
            Defaults to [loky.get_reusable_executor()][loky.get_reusable_executor],
            which uses the `loky` multiprocessing context
            ([more info](https://loky.readthedocs.io/en/stable/API.html#processes-start-methods-in-loky)).
            If [loky][loky] is not installed defaults to Standard Library's
            [ProcessPoolExecutor][concurrent.futures.ProcessPoolExecutor] with the `spawn` multiprocessing
            start method ([more info](https://docs.python.org/3/library/multiprocessing.html#multiprocessing-start-methods))
            Users should control the Pool's configuration (e.g. number of workers) by passing
            a custom `Executor` instance.
        check: If `True` then if any of the `func` calls raised an exception, an
            [ExceptionGroup][ExceptionGroup] containing all the exceptions will be raised.
        include_kwargs: A boolean flag indicating whether the keyword arguments of the
            functions will be present in the [FurureResult][multifutures.FutureResult]
            object. Useful for keeping memory usage down when the input are objects like
            `xarray.Dataset` etc.
        progress_bar: An instance of a progress bar implementing the `tqdm` API. Defaults to
            `tqdm.auto.tqdm`. If you want to disable it you can do so by passing `disable=True`
            when creating the `progress_bar`.

                progress_bar = tqdm.auto.tqdm(func_kwargs, disable=True)
                results = multiprocess(func, func_kwargs, progress_bar=progress_bar)

    Returns:
        A list of [FutureResult][multifutures.FutureResult] objects. Each object
            will contain the output of `func(**func_kwargs[i])` or an `Exception`.

    Raises:
        exceptiongroup.ExceptionGroup: If any of the function calls raises an exception and `check` is True.

    """
    executor = _resolve_multiprocess_executor(executor)
    results = _multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        include_kwargs=include_kwargs,
        progress_bar=progress_bar,
        check=check,
    )
    return results
