from __future__ import annotations

import os
import subprocess

import pytest

from multifutures.utils import async_run
from multifutures.utils import run


MISSING_FILE_ERROR = 127


def assert_processes_equal(cp1, cp2) -> None:
    assert cp1.args == cp2.args
    assert cp1.returncode == cp2.returncode
    assert cp1.stdout == cp2.stdout
    assert cp1.stderr == cp2.stderr


@pytest.mark.parametrize(
    "cmd",
    [
        pytest.param("echo 111", id="str"),
        pytest.param(b"echo 111", id="bytes"),
        pytest.param(["echo", "111"], id="sequence of strings"),
        pytest.param([b"echo", b"111"], id="sequence of bytes"),
    ],
)
def test_run_cmd_types(cmd, capfd):
    proc = run(cmd)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert isinstance(proc.stdout, str)
    assert isinstance(proc.stderr, str)
    assert proc.stdout
    assert "111\n" == proc.stdout
    assert not proc.stderr
    assert proc.returncode == 0
    sys_out, sys_err = capfd.readouterr()
    assert "111\n" == sys_out
    assert not sys_err


def test_run_silence_stdout_and_stderr(capfd):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="111\n", stderr="222\n")
    proc = run(cmd, echo_stdout=False, echo_stderr=False)
    assert_processes_equal(proc, expected)
    sys_stdout, sys_stderr = capfd.readouterr()
    assert not sys_stdout
    assert not sys_stderr


def test_run_capture_just_stderr():
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="222\n")
    proc = run(cmd, stdout=None)
    assert_processes_equal(proc, expected)


def nest_run_capture_just_stdout():
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="111\n", stderr="")
    proc = run(cmd, stderr=None)
    assert_processes_equal(proc, expected)


def test_run_capture_both_stdout_and_stderr(capfd):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="111\n", stderr="222\n")
    proc = run(cmd)
    assert_processes_equal(proc, expected)
    sys_stdout, sys_stderr = capfd.readouterr()
    assert sys_stdout == "111\n"
    assert sys_stderr == "222\n"


@pytest.mark.parametrize("echo", [pytest.param(True, id="echo=True"), pytest.param(False, id="echo=False")])
def test_run_capture_both_stdout_and_stderr_using_file_descriptors(capfd, tmp_path, echo):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
    stdout_file, stderr_file = tmp_path / "stdout.txt", tmp_path / "stderr.txt"
    with stdout_file.open("w") as stdout_fd, stderr_file.open("w") as stderr_fd:
        proc = run(cmd, stdout=stdout_fd, stderr=stderr_fd, echo_stdout=echo, echo_stderr=echo)
    assert_processes_equal(proc, expected)
    assert stdout_file.read_text() == "111\n"
    assert stderr_file.read_text() == "222\n"
    # Regardless of the value of `echo`, nothing gets echoed to console
    sys_stdout, sys_stderr = capfd.readouterr()
    assert not sys_stdout
    assert not sys_stderr


def test_run_no_capture_using_devnull(capfd):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
    proc = run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert_processes_equal(proc, expected)
    sys_stdout, sys_stderr = capfd.readouterr()
    assert not sys_stdout
    assert not sys_stderr


@pytest.mark.parametrize("echo", [pytest.param(True, id="echo=True"), pytest.param(False, id="echo=False")])
def test_run_no_capture_using_none(capfd, echo):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
    proc = run(cmd, stdout=None, stderr=None, echo_stdout=echo, echo_stderr=echo)
    assert_processes_equal(proc, expected)
    # Regardless of the value of `echo`, the results get printed to the console
    sys_stdout, sys_stderr = capfd.readouterr()
    assert sys_stdout == "111\n"
    assert sys_stderr == "222\n"


def test_run_merge_stderr_in_stdout(capfd):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="111\n222\n", stderr="")
    proc = run(cmd, stderr=subprocess.STDOUT)
    assert_processes_equal(proc, expected)
    sys_stdout, sys_stderr = capfd.readouterr()
    assert sys_stdout == "111\n222\n"
    assert sys_stderr == ""


@pytest.mark.xfail
def test_run_merge_stderr_in_stdout_when_stdout_is_a_file_descriptor(tmp_path, capfd):
    cmd = "echo 111; echo 222 > /dev/stderr"
    expected = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
    output_file = tmp_path / "out.txt"
    with output_file.open("w+") as fd:
        proc = run(cmd, stdout=fd, stderr=subprocess.STDOUT)
    assert_processes_equal(proc, expected)
    sys_stdout, sys_stderr = capfd.readouterr()
    assert sys_stdout == ""
    assert sys_stderr == ""
    assert output_file.read_text() == "111\n222\n"


def test_run_error_no_check():
    cmd = "missing_command"
    expected = subprocess.CompletedProcess(
        args=cmd,
        returncode=MISSING_FILE_ERROR,
        stdout="",
        stderr=f"/bin/sh: line 1: {cmd}: command not found\n",
    )
    proc = run(cmd, check=False)
    assert_processes_equal(proc, expected)


def test_run_error_check():
    cmd = "missing_command"
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
