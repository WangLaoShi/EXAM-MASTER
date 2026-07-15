#!/usr/bin/env python3
"""
Development server runner
"""

import os
import signal
import socket
import subprocess
import sys
import time

import uvicorn

HOST = "0.0.0.0"
PORT = 8000


def _pids_on_port_windows(port: int) -> set[int]:
    pids: set[int] = set()
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        output = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            errors="replace",
            creationflags=flags,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return pids

    needle = f":{port}"
    for line in output.splitlines():
        if "LISTENING" not in line.upper() or needle not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            pass
    return pids


def _pids_on_port_unix(port: int) -> set[int]:
    for cmd in (
        ["lsof", "-ti", f":{port}", "-sTCP:LISTEN"],
        ["lsof", "-ti", f":{port}"],
    ):
        try:
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        pids = set()
        for token in output.split():
            try:
                pids.add(int(token))
            except ValueError:
                pass
        if pids:
            return pids
    return set()


def _pids_on_port(port: int) -> set[int]:
    if sys.platform == "win32":
        return _pids_on_port_windows(port)
    return _pids_on_port_unix(port)


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            creationflags=flags,
        )
        output = result.stdout or ""
        return str(pid) in output and "No tasks are running" not in output
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _port_is_free(port: int, host: str = HOST) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _kill_pid(pid: int) -> None:
    if pid == os.getpid() or not _process_exists(pid):
        return
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
            if _process_exists(pid):
                os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def free_port(port: int) -> None:
    """若端口已被占用，结束占用该端口的进程（不含当前进程）。"""
    if _port_is_free(port):
        return

    own_pid = os.getpid()
    for pid in _pids_on_port(port):
        if pid in (own_pid, 0):
            continue
        print(f"Port {port} in use by PID {pid}, terminating...")
        _kill_pid(pid)

    for _ in range(30):
        if _port_is_free(port):
            return
        time.sleep(0.2)

    if not _port_is_free(port):
        remaining = sorted(_pids_on_port(port) - {own_pid, 0})
        print(
            f"Warning: port {port} still in use"
            + (f" (PIDs: {remaining})" if remaining else ""),
            file=sys.stderr,
        )


if __name__ == "__main__":
    free_port(PORT)
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
