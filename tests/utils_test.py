from __future__ import annotations

import os
import subprocess

import pytest

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
def test_run_stdout(cmd):
    proc = run(cmd)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert proc.stdout
    assert "111" in proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


def test_run_stderr():
    value = 111
    cmd = f"echo {value} > /dev/stderr"
    proc = run(cmd)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert not proc.stdout
    assert proc.stderr
    assert proc.stderr.strip() == f"{value}"
    assert proc.returncode == 0


def test_run_no_capture():
    value = 111
    cmd = f"echo {value} && echo {value} > /dev/stderr"
    proc = run(cmd, stdout=None, stderr=None)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert not proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0


def test_run_just_stderr():
    value = 111
    cmd = f"echo {value} && echo {value} > /dev/stderr"
    proc = run(cmd, stdout=None, stderr=subprocess.PIPE)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert not proc.stdout
    assert proc.stderr
    assert proc.returncode == 0


def test_run_both_stdout_and_stderr():
    value = 111
    cmd = f"echo {value} && echo {value} > /dev/stderr"
    proc = run(cmd)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert proc.stdout
    assert proc.stdout.strip() == f"{value}"
    assert proc.stderr
    assert proc.stderr.strip() == f"{value}"
    assert proc.returncode == 0


def test_combine_stdout_and_stderr():
    value = 111
    cmd = f"echo {value} && echo {value} > /dev/stderr"
    proc = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert proc.stdout
    assert proc.stdout.strip() == f"{value}\n{value}"
    assert not proc.stderr
    assert proc.returncode == 0


def test_run_error_no_check():
    cmd = "asdf"
    proc = run(cmd, check=False)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert not proc.stdout
    assert isinstance(proc.stderr, str)
    assert proc.stderr
    assert cmd in proc.stderr.strip()
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


@pytest.mark.parametrize("timeout", [0, 0.1])
def test_run_timeout(timeout):
    with pytest.raises(subprocess.TimeoutExpired):
        run("sleep 1", timeout=timeout)


def test_pass_env():
    variable = "AAA"
    value = "111"
    proc = run("env", env={variable: value})
    assert variable not in os.environ
    assert proc.returncode == 0
    assert f"{variable}={value}" in proc.stdout
