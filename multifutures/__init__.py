from __future__ import annotations

import importlib.metadata

from ._common import ExecutorProtocol
from ._common import ProgressBarProtocol
from ._multi import check_results
from ._multi import FutureResult
from ._multi import multiprocess
from ._multi import multithread
from ._rate_limit import RateLimit
from ._rate_limit import wait

__version__ = importlib.metadata.version("multifutures")

__all__: list[str] = [
    "__version__",
    # common
    "ExecutorProtocol",
    "ProgressBarProtocol",
    # multi
    "check_results",
    "FutureResult",
    "multiprocess",
    "multithread",
    # rate_limit
    "RateLimit",
    "wait",
]
