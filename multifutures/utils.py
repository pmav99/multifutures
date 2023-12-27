from __future__ import annotations

import io
import os
import subprocess
import sys
import typing as T
from collections.abc import Mapping
from collections.abc import Sequence

import anyio
from anyio.abc import AnyByteReceiveStream
from anyio.streams.text import TextReceiveStream


async def handle_stream(input_stream: TextReceiveStream, output_stream: T.IO[str], buffer: io.StringIO) -> None:
    async for line in input_stream:
        output_stream.write(line)
        buffer.write(line)


async def async_run(
    cmd: str | bytes | Sequence[str | bytes],
    *,
    stdout: int | T.IO[str] | None = subprocess.PIPE,
    stderr: int | T.IO[str] | None = subprocess.PIPE,
    check: bool = False,
    timeout: float = 5,
    cwd: str | bytes | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    start_new_session: bool = False,
    **kwargs: T.Any,
) -> subprocess.CompletedProcess[str]:
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
                if stdout or stderr:
                    async with anyio.create_task_group() as tg:
                        if stdout:
                            transport_stream = T.cast(AnyByteReceiveStream, proc.stdout)
                            proc_stdout = TextReceiveStream(transport_stream=transport_stream)
                            tg.start_soon(handle_stream, proc_stdout, sys.stdout, stdout_buffer, name="stdout")

                        if stderr != subprocess.STDOUT:
                            transport_stream = T.cast(AnyByteReceiveStream, proc.stderr)
                            proc_stderr = TextReceiveStream(transport_stream=transport_stream)
                            tg.start_soon(handle_stream, proc_stderr, sys.stderr, stderr_buffer, name="stderr")

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
    start_new_session: bool = False,
    **kwargs: T.Any,
) -> subprocess.CompletedProcess[str]:
    proc = anyio.run(
        lambda: async_run(
            cmd=cmd,
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
