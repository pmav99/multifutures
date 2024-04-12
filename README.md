# multifutures

[![PyPI - Version](https://img.shields.io/pypi/v/multifutures.svg)](https://pypi.org/project/multifutures)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/multifutures.svg)](https://pypi.org/project/multifutures)
[![ci](https://github.com/pmav99/multifutures/workflows/test/badge.svg)](https://github.com/pmav99/multifutures/actions?query=workflow%3Atest)

A library that simplifies using multithreading/multiprocessing pools

---

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

```console
python -mpip install multifutures
```

## Usage

``` python
import multifutures as mf


def return_square(number: float) -> float:
    squared = number**2
    return squared


results = mf.multiprocess(
    func=return_square,
    func_kwargs=[{"number": i} for i in range(10)],
)

for result in results:
    print(result)
```

Will print:

```
FutureResult(exception=None, kwargs={'number': 0}, result=0)
FutureResult(exception=None, kwargs={'number': 1}, result=1)
FutureResult(exception=None, kwargs={'number': 2}, result=4)
FutureResult(exception=None, kwargs={'number': 3}, result=9)
FutureResult(exception=None, kwargs={'number': 4}, result=16)
FutureResult(exception=None, kwargs={'number': 5}, result=25)
FutureResult(exception=None, kwargs={'number': 6}, result=36)
FutureResult(exception=None, kwargs={'number': 7}, result=49)
FutureResult(exception=None, kwargs={'number': 8}, result=64)
FutureResult(exception=None, kwargs={'number': 9}, result=81)
```


## License

`multifutures` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
