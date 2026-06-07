import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from api_runtime import (
    LOG_PATH,
    PROJECT_ROOT,
    START_LOCK_PATH,
    STOP_REQUEST_PATH,
    api_is_healthy,
    ensure_directories,
    find_available_port,
    is_current_api,
    process_is_alive,
    read_status,
    remove_status,
    status_is_running,
    stop_process,
    utc_now_text,
    write_status,
)


MAX_RESTARTS = 5
STARTUP_TIMEOUT_SECONDS = 35
STABLE_SECONDS = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动并守护 FastAPI 后端。")
    parser.add_argument("--supervise", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--python", help=argparse.SUPPRESS)
    return parser.parse_args()


def api_command(python: Path, port: int) -> list[str]:
    return [
        str(python),
        "-m",
        "uvicorn",
        "src.api:app",
        "--app-dir",
        str(PROJECT_ROOT),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
    ]


def copy_output(process: subprocess.Popen) -> None:
    if process.stdout is None:
        return
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()


def supervise(port: int, python: Path) -> int:
    ensure_directories()
    command = api_command(python, port)
    restart_count = 0
    supervisor_pid = os.getpid()

    while restart_count <= MAX_RESTARTS:
        if STOP_REQUEST_PATH.exists():
            STOP_REQUEST_PATH.unlink(missing_ok=True)
            remove_status()
            return 0

        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONUTF8": "1"},
            creationflags=(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            ),
        )
        threading.Thread(
            target=copy_output,
            args=(process,),
            daemon=True,
        ).start()
        status = {
            "pid": process.pid,
            "supervisor_pid": supervisor_pid,
            "port": port,
            "url": f"http://localhost:{port}",
            "project_root": str(PROJECT_ROOT.resolve()),
            "log_file": str(LOG_PATH.resolve()),
            "state": "starting",
            "restart_count": restart_count,
            "started_at": utc_now_text(),
        }
        write_status(status)

        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if STOP_REQUEST_PATH.exists() or process.poll() is not None:
                break
            if api_is_healthy(port):
                status["state"] = "running"
                write_status(status)
                break
            time.sleep(0.5)

        if status.get("state") != "running":
            stop_process(process.pid)
            if STOP_REQUEST_PATH.exists():
                STOP_REQUEST_PATH.unlink(missing_ok=True)
                remove_status()
                return 0
            restart_count += 1
            continue

        running_since = time.monotonic()
        while process.poll() is None:
            if STOP_REQUEST_PATH.exists():
                stop_process(process.pid)
                STOP_REQUEST_PATH.unlink(missing_ok=True)
                remove_status()
                return 0
            if time.monotonic() - running_since >= STABLE_SECONDS:
                restart_count = 0
            time.sleep(1)
        restart_count += 1

    failed = read_status() or {}
    failed.update(
        {
            "state": "failed",
            "last_error": "FastAPI 连续重启达到上限，请检查日志。",
        }
    )
    write_status(failed)
    return 1


def acquire_lock() -> bool:
    ensure_directories()
    try:
        descriptor = os.open(
            START_LOCK_PATH,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError:
        try:
            if time.time() - START_LOCK_PATH.stat().st_mtime > 60:
                START_LOCK_PATH.unlink(missing_ok=True)
                return acquire_lock()
        except OSError:
            pass
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
        lock_file.write(str(os.getpid()))
    return True


def launch_supervisor(port: int, python: Path) -> int:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--supervise",
        "--port",
        str(port),
        "--python",
        str(python),
    ]
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ),
    )
    return process.pid


def start() -> int:
    ensure_directories()
    if not acquire_lock():
        print("另一个 FastAPI 启动操作正在进行。")
        return 1
    try:
        status = read_status()
        if status_is_running(status):
            print(f"FastAPI 后端已经在运行：{status['url']}")
            return 0
        if status:
            pid = int(status.get("pid", 0))
            if process_is_alive(pid) and is_current_api(pid):
                stop_process(pid)
        remove_status()
        STOP_REQUEST_PATH.unlink(missing_ok=True)

        try:
            import fastapi  # noqa: F401
            import uvicorn  # noqa: F401
        except ImportError:
            print("FastAPI 启动失败，请先运行：pip install -r requirements.txt")
            return 1

        port = find_available_port()
        supervisor_pid = launch_supervisor(port, Path(sys.executable))
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS + 5
        while time.monotonic() < deadline:
            status = read_status()
            if (
                status
                and int(status.get("supervisor_pid", 0)) == supervisor_pid
                and status_is_running(status)
            ):
                print("====================================")
                print("FastAPI 后端已启动")
                print(f"接口地址：{status['url']}")
                print("日志文件：logs/api_backend.log")
                print("====================================")
                return 0
            if not process_is_alive(supervisor_pid):
                break
            time.sleep(0.5)
        print("FastAPI 后端启动失败，请查看 logs/api_backend.log。")
        return 1
    finally:
        START_LOCK_PATH.unlink(missing_ok=True)


def main() -> None:
    args = parse_args()
    if args.supervise:
        if not args.port or not args.python:
            raise SystemExit(2)
        raise SystemExit(supervise(args.port, Path(args.python)))
    raise SystemExit(start())


if __name__ == "__main__":
    main()
