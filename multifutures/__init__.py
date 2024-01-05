from __future__ import annotations

import importlib

from multifutures.multi import check_results
from multifutures.multi import FutureResult
from multifutures.multi import multiprocess
from multifutures.multi import multithread
from multifutures.rate_limit import RateLimit
from multifutures.rate_limit import wait
from multifutures.utils import async_run
from multifutures.utils import run

__version__ = importlib.metadata.version("multifutures")

__all__: list[str] = [
    "check_results",
    "FutureResult",
    "multiprocess",
    "multithread",
    "RateLimit",
    "__version__",
    "wait",
    # utils
    "async_run",
    "run",
]
