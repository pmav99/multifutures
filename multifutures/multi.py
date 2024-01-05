from __future__ import annotations

import logging
import textwrap
import typing as T
from collections.abc import Callable
from concurrent.futures import as_completed
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import exceptiongroup
import loky
import pydantic
import tqdm.auto


logger = logging.getLogger(__name__)


class FutureResult(pydantic.BaseModel):
    """
    The results of a function executed via
    [multiprocess][multifutures.multiprocess] or [multithread][multifutures.multithread].
    """

    exception: T.Annotated[
        T.Union[Exception, None],  # noqa: UP007 - Use X | Y for type annotations
        pydantic.Field(
            description=textwrap.dedent(
                """
                `exception` will be `None` unless an `Exception` has been raised
                during the function execution in which case the attribute will
                contain the exception object.
                """,
            ),
        ),
    ] = None
    kwargs: T.Annotated[
        T.Union[dict[str, T.Any], None],  # noqa: UP007 - Use X | Y for type annotations
        pydantic.Field(
            description=textwrap.dedent(
                """
                `kwargs` may contain the keyword arguments that were used in the function call.
                If the objects passed as `kwargs` are too big, e.g. big dataframes, you can omit them
                by passing `include_kwargs=False` in
                [multiprocess][multifutures.multiprocess]/[multithread][multifutures.multithread]".
                """,
            ),
        ),
    ] = None
    result: T.Annotated[
        T.Any,
        pydantic.Field(
            description=textwrap.dedent(
                """
                `result` will contain the function's output.
                If an `Exception` has been raised, then it will be `None`.
                """,
            ),
        ),
    ] = None

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


def check_results(results: list[FutureResult]) -> None:
    """
    Raises `ValueError` if any of the [results] contains an exception.

    Raises:
        ValueError: "asdf  asdfasdf
    """

    exceptions = [r.exception for r in results if r.exception is not None]
    if exceptions:
        exception_group = exceptiongroup.ExceptionGroup("There were exceptions", exceptions)
        raise exception_group


def multi(
    *,
    executor: ProcessPoolExecutor | ThreadPoolExecutor | loky.ProcessPoolExecutor,
    func: Callable[..., T.Any],
    func_kwargs: list[dict[str, T.Any]],
    include_kwargs: bool,
    disable_progress_bar: bool,
    check: bool,
) -> list[FutureResult]:
    with tqdm.auto.tqdm(total=len(func_kwargs), disable=disable_progress_bar) as progress_bar:
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
    func: Callable[..., T.Any],
    func_kwargs: list[dict[str, T.Any]],
    *,
    executor: ThreadPoolExecutor | None = None,
    include_kwargs: bool = True,
    disable_progress_bar: bool = False,
    check: bool = False,
) -> list[FutureResult]:
    """

    Returns:
        A list of [FutureResult][multifutures.FutureResult] objects. Each object
            will contain the output of `func(**func_kwarg)` or an `Exception`.

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code and `check` is True.

    """
    if executor is None:
        executor = ThreadPoolExecutor()
    results = multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        include_kwargs=include_kwargs,
        disable_progress_bar=disable_progress_bar,
        check=check,
    )
    return results


def multiprocess(
    func: Callable[..., T.Any],
    func_kwargs: list[dict[str, T.Any]],
    *,
    executor: loky.ProcessPoolExecutor | None = None,
    include_kwargs: bool = True,
    disable_progress_bar: bool = False,
    check: bool = False,
) -> list[FutureResult]:
    """
    Returns:
        A list of [FutureResult][multifutures.FutureResult] objects. Each object
            will contain the output of `func(**func_kwarg)` or an `Exception`.

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code and `check` is True.

    """
    if executor is None:
        executor = loky.ProcessPoolExecutor(timeout=None)
    results = multi(
        executor=executor,
        func=func,
        func_kwargs=func_kwargs,
        include_kwargs=include_kwargs,
        disable_progress_bar=disable_progress_bar,
        check=check,
    )
    return results
