## `multifutures`

Multiprocessing/multithreading made easy!

### Example


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
