from __future__ import annotations

import types
import typing as T
from concurrent.futures import Future


if T.TYPE_CHECKING:
    try:
        from typing import Self  # type: ignore[attr-defined]
    except ImportError:
        from typing_extensions import Self


__all__ = [
    "ExecutorProtocol",
    "ProgressBarProtocol",
]


# Protocols
class ProgressBarProtocol(T.Protocol):
    def update(self, n: float | None) -> bool | None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    def __enter__(self) -> Self:
        raise NotImplementedError()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool | None:
        raise NotImplementedError()


class ExecutorProtocol(T.Protocol):
    def submit(self, fn: T.Callable[..., T.Any], /, *args: T.Any, **kwargs: T.Any) -> Future[T.Any]:
        raise NotImplementedError()

    def __enter__(self) -> Self:
        raise NotImplementedError()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool | None:
        raise NotImplementedError()
