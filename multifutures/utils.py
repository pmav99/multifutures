from __future__ import annotations

import io
import os
import subprocess
import sys
import typing as T
from collections.abc import Mapping
from collections.abc import Sequence

import anyio
from anyio.streams.text import TextReceiveStream


async def handle_stream(
    input_stream: TextReceiveStream,
    buffer: io.StringIO,
    output_stream: T.IO[str],
    echo: bool,  # noqa: FBT001
) -> None:
    async for line in input_stream:
        buffer.write(line)
        if echo:
            output_stream.write(line)


async def async_run(
    cmd: str | bytes | Sequence[str | bytes],
    *,
    stdout: int | T.IO[str] | None = subprocess.PIPE,
    stderr: int | T.IO[str] | None = subprocess.PIPE,
    check: bool = False,
    timeout: float = 5,
    cwd: str | bytes | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    echo_stdout: bool = True,
    echo_stderr: bool = True,
    start_new_session: bool = False,
    **kwargs: T.Any,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command asynchronously and return a `subprocess.CompletedProcess`.

    The `stdout` and `stderr` parameters are used to specify where the standard output and
    standard error of the command should be directed. Documentation of the supported values
    is provided in the [StdLib docs](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.subprocess_exec).

    By default, both `stdout` and `stderr` are set to `subprocess.PIPE`, which means that the output
    and error are captured and available to you in the `CompletedProcess` object returned by the function.
    This allows you to programmatically access and manipulate the command's output and error.

    `echo_stdout` and `echo_stderr` affect whether the output or error will get printed to the console or not.
    In certain cases, depending on the values you pass to `stdout` and `stderr`, these arguments might have no
    effect (for example if you pass an open file then `echo_output` and `echo_stderr` are ignored).

    Args:
        cmd: The command to run.
        stdout: The standard output option. Defaults to subprocess.PIPE.
        stderr: The standard error option. Defaults to subprocess.PIPE.
        check: If True, checks the return code. Defaults to False.
        timeout: The timeout for the command. Defaults to 5.
        cwd: The working directory. Defaults to None.
        env: The environment variables. Defaults to None.
        echo_stdout: If True, echoes the stdout command output. Defaults to True.
        echo_stderr: If True, echoes the stderr command output. Defaults to True.
        start_new_session: If True, starts a new session. Defaults to False.
        **kwargs: Additional keyword arguments to be passed to `anyio.open_process()`.

    Returns:
        subprocess.CompletedProcess: The completed process.

    Raises:
        subprocess.TimeoutExpired: If the command times out.
        subprocess.CalledProcessError: If the command returns a non-zero exit code and `check` is True.
    """
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    proc = await anyio.open_process(
        command=cmd,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        start_new_session=start_new_session,
        **kwargs,
    )
    try:
        with anyio.fail_after(timeout):
            async with proc:
                async with anyio.create_task_group() as tg:
                    if proc.stdout is not None:
                        proc_stdout = TextReceiveStream(transport_stream=proc.stdout)
                        tg.start_soon(handle_stream, proc_stdout, stdout_buffer, sys.stdout, echo_stdout)

                    if proc.stderr is not None:
                        proc_stderr = TextReceiveStream(transport_stream=proc.stderr)
                        tg.start_soon(handle_stream, proc_stderr, stderr_buffer, sys.stderr, echo_stderr)

                if proc.returncode is None:
                    await proc.wait()

    except TimeoutError as exc:
        raise subprocess.TimeoutExpired(
            cmd=cmd,
            timeout=timeout,
            output=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
        ) from exc

    if check and proc.returncode:
        raise subprocess.CalledProcessError(
            cmd=cmd,
            returncode=proc.returncode,
            output=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
        )

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=T.cast(int, proc.returncode),
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
    )


def run(
    cmd: str | bytes | Sequence[str | bytes],
    *,
    stdout: int | T.IO[str] | None = subprocess.PIPE,
    stderr: int | T.IO[str] | None = subprocess.PIPE,
    check: bool = False,
    timeout: float = 5,
    cwd: str | bytes | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    echo_stdout: bool = True,
    echo_stderr: bool = True,
    start_new_session: bool = False,
    **kwargs: T.Any,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command and return a `subprocess.CompletedProcess`.

    The `stdout` and `stderr` parameters are used to specify where the standard output and
    standard error of the command should be directed. Documentation of the supported values
    is provided in the [StdLib docs](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.subprocess_exec).

    By default, both `stdout` and `stderr` are set to `subprocess.PIPE`, which means that the output
    and error are captured and available to you in the `CompletedProcess` object returned by the function.
    This allows you to programmatically access and manipulate the command's output and error.

    `echo_stdout` and `echo_stderr` affect whether the output or error will get printed to the console or not.
    In certain cases, depending on the values you pass to `stdout` and `stderr`, these arguments might have no
    effect (for example if you pass an open file then `echo_output` and `echo_stderr` are ignored).

    Args:
        cmd: The command to run.
        stdout: The standard output option. Defaults to subprocess.PIPE.
        stderr: The standard error option. Defaults to subprocess.PIPE.
        check: If True, checks the return code. Defaults to False.
        timeout: The timeout for the command. Defaults to 5.
        cwd: The working directory. Defaults to None.
        env: The environment variables. Defaults to None.
        echo_stdout: If True, echoes the stdout command output. Defaults to True.
        echo_stderr: If True, echoes the stderr command output. Defaults to True.
        start_new_session: If True, starts a new session. Defaults to False.
        **kwargs: Additional keyword arguments to be passed to `anyio.open_process()`.

    Returns:
        subprocess.CompletedProcess: The completed process.

    Raises:
        subprocess.TimeoutExpired: If the command times out.
        subprocess.CalledProcessError: If the command returns a non-zero exit code and `check` is True.

    """
    proc = anyio.run(
        lambda: async_run(
            cmd=cmd,
            echo_stdout=echo_stdout,
            echo_stderr=echo_stderr,
            stdout=stdout,
            stderr=stderr,
            check=check,
            timeout=timeout,
            cwd=cwd,
            env=env,
            start_new_session=start_new_session,
            **kwargs,
        ),
    )
    return proc
