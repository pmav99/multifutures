from __future__ import annotations

import importlib


def test_import():
    import multifutures

    del multifutures


def test_version():
    import multifutures

    assert multifutures.__version__ == importlib.metadata.version("multifutures")
