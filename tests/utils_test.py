from __future__ import annotations

import os
import subprocess
import sys

import pytest

from multifutures.utils import async_run
from multifutures.utils import run


MISSING_FILE_ERROR = 127


@pytest.mark.parametrize(
    "cmd",
    [
        pytest.param("echo 111", id="str"),
        pytest.param(b"echo 111", id="bytes"),
        pytest.param(["echo", "111"], id="sequence of strings"),
        pytest.param([b"echo", b"111"], id="sequence of bytes"),
    ],
)
def test_run_cmd_types(cmd):
    proc = run(cmd)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert proc.stdout
    assert "111" in proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


def test_run_capture_both_stdout_and_stderr():
    stdout_value, stderr_value = "111", "222"
    cmd = f"echo {stdout_value}; echo {stderr_value} > /dev/stderr"
    proc = run(cmd)
    assert proc.stdout
    assert stdout_value in proc.stdout
    assert proc.stderr
    assert stderr_value in proc.stderr
    assert proc.returncode == 0


def test_run_capture_both_stdout_and_stderr_into_files(tmp_path):
    stdout_value, stderr_value = "111", "222"
    cmd = f"echo {stdout_value}; echo {stderr_value} > /dev/stderr"
    stdout_file = tmp_path / "stdout.txt"
    stderr_file = tmp_path / "stderr.txt"
    with stdout_file.open("w") as stdout_fh, stderr_file.open("w") as stderr_fh:
        proc = run(cmd, stdout=stdout_fh, stderr=stderr_fh)
    assert not proc.stdout
    assert not proc.stderr
    assert stdout_value in stdout_file.read_text()
    assert stderr_value in stderr_file.read_text()
    assert proc.returncode == 0


def test_run_capture_just_stdout():
    stdout_value, stderr_value = "111", "222"
    cmd = f"echo {stdout_value}; echo {stderr_value} > /dev/stderr"
    proc = run(cmd, stderr=None)
    assert stdout_value in proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


def test_run_capture_just_stderr():
    stdout_value, stderr_value = "111", "222"
    cmd = f"echo {stdout_value}; echo {stderr_value} > /dev/stderr"
    proc = run(cmd, stdout=None)
    assert not proc.stdout
    assert stderr_value in proc.stderr
    assert proc.returncode == 0


@pytest.mark.parametrize("stream", [pytest.param(subprocess.DEVNULL, id="/dev/null"), None])
def test_run_no_capture(stream):
    stdout_value, stderr_value = "111", "222"
    cmd = f"echo {stdout_value}; echo {stderr_value} > /dev/stderr"
    proc = run(cmd, stdout=stream, stderr=stream)
    assert not proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


def test_merge_stderr_in_stdout():
    stdout_value, stderr_value = "111", "222"
    cmd = f"echo {stdout_value}; echo {stderr_value} > /dev/stderr"
    proc = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert proc.stdout
    assert stdout_value in proc.stdout
    assert stderr_value in proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


def test_run_error_no_check():
    cmd = "missing_command"
    proc = run(cmd, check=False)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert not proc.stdout
    assert cmd in proc.stderr
    assert proc.returncode == MISSING_FILE_ERROR


def test_run_error_check():
    cmd = "asdf"
    with pytest.raises(subprocess.CalledProcessError) as exc:
        run(cmd, check=True)
    main_exc = exc.value
    assert main_exc.cmd == cmd
    assert isinstance(main_exc.stdout, str)
    assert not main_exc.stdout
    assert isinstance(main_exc.stderr, str)
    assert main_exc.stderr
    assert cmd in main_exc.stderr
    assert main_exc.returncode == MISSING_FILE_ERROR


@pytest.mark.parametrize("timeout", [0, 0.01])
def test_run_timeout(timeout):
    with pytest.raises(subprocess.TimeoutExpired):
        run("sleep 1", timeout=timeout)


def test_run_env():
    variable = "variable"
    value = "111"
    proc = run("env", env={variable: value})
    assert variable not in os.environ
    assert f"{variable}={value}" in proc.stdout
    assert proc.returncode == 0


def test_run_cwd(tmp_path):
    cwd = tmp_path
    proc = run("pwd", cwd=cwd)
    assert str(cwd) in proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


@pytest.mark.anyio
async def test_async_run():
    # Test a simple command
    result = await async_run(["echo", "Hello, Async World!"])
    assert result.stdout.strip() == "Hello, Async World!"

    # Test a command that fails
    with pytest.raises(subprocess.CalledProcessError):
        await async_run(["ls", "/nonexistentdirectory"], check=True)

    # Test a command that times out
    with pytest.raises(subprocess.TimeoutExpired):
        await async_run(["sleep", "10"], timeout=0.01)
