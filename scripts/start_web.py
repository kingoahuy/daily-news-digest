import argparse
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from web_runtime import (
    APP_PATH,
    DEFAULT_PORT,
    LOG_PATH,
    PROJECT_ROOT,
    START_LOCK_PATH,
    STATUS_PATH,
    STOP_REQUEST_PATH,
    SCHEDULER_LOG_PATH,
    SCHEDULER_STATUS_PATH,
    display_relative_path,
    ensure_runtime_directories,
    find_available_port,
    find_existing_project_service,
    find_streamlit_python,
    is_current_project_streamlit,
    is_current_project_scheduler,
    port_is_open,
    process_is_alive,
    read_status,
    remove_status,
    status_is_running,
    streamlit_is_healthy,
    terminate_process,
    utc_now_text,
    write_status,
)


MAX_RESTARTS = 5
STARTUP_TIMEOUT_SECONDS = 35
STABLE_SECONDS = 60
SENSITIVE_ENV_NAMES = (
    "DEEPSEEK_API_KEY",
    "SMTP_PASSWORD",
    "SMTP_USER",
    "MAIL_FROM",
    "MAIL_TO",
)
LOG_LOCK = threading.Lock()


def load_sensitive_values() -> list[str]:
    """读取环境变量和本地 .env，仅用于日志内容脱敏。"""

    values = []
    env_path = PROJECT_ROOT / ".env"
    file_values: Dict[str, str] = {}
    if env_path.exists():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                file_values[name.strip()] = value.strip().strip("\"'")
        except OSError:
            pass

    for name in SENSITIVE_ENV_NAMES:
        value = os.environ.get(name, "") or file_values.get(name, "")
        if value and len(value) >= 4:
            values.append(value)
    return values


SENSITIVE_VALUES = load_sensitive_values()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="启动并守护每日热点新闻知识库网页。"
    )
    parser.add_argument("--supervise", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--streamlit-python", help=argparse.SUPPRESS)
    parser.add_argument("--adopt-pid", type=int, default=0, help=argparse.SUPPRESS)
    return parser.parse_args()


def log_message(message: str) -> None:
    ensure_runtime_directories()
    line = f"[{utc_now_text()}] {message}\n"
    with LOG_LOCK:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(line)


def redact_log_line(line: str) -> str:
    redacted = line
    for value in SENSITIVE_VALUES:
        redacted = redacted.replace(value, "<SENSITIVE_VALUE_REDACTED>")
    redacted = re.sub(
        r"(?i)(api[_-]?key|smtp[_-]?password|authorization)"
        r"(\s*[=:]\s*)[^\s,;]+",
        r"\1\2<REDACTED>",
        redacted,
    )
    return redacted


def copy_process_output(process: subprocess.Popen) -> None:
    if process.stdout is None:
        return
    for line in process.stdout:
        safe_line = redact_log_line(line)
        with LOG_LOCK:
            with LOG_PATH.open("a", encoding="utf-8") as log_file:
                log_file.write(safe_line)


def streamlit_command(python_executable: Path, port: int) -> list[str]:
    return [
        str(python_executable),
        "-m",
        "streamlit",
        "run",
        str(APP_PATH),
        "--server.port",
        str(port),
        "--server.address",
        "localhost",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]


def build_status(
    pid: int,
    supervisor_pid: int,
    port: int,
    command: list[str],
    restart_count: int,
    state: str = "starting",
    last_error: str = "",
) -> Dict[str, object]:
    status = {
        "pid": pid,
        "supervisor_pid": supervisor_pid,
        "port": port,
        "url": f"http://localhost:{port}",
        "started_at": utc_now_text(),
        "command": subprocess.list2cmdline(command),
        "log_file": str(LOG_PATH.resolve()),
        "project_root": str(PROJECT_ROOT.resolve()),
        "restart_count": restart_count,
        "state": state,
        "last_error": last_error,
    }
    existing = read_status() or {}
    for key in ("scheduler_pid", "scheduler_log_file"):
        if existing.get(key):
            status[key] = existing[key]
    return status


def wait_until_healthy(process: subprocess.Popen, port: int) -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if STOP_REQUEST_PATH.exists() or process.poll() is not None:
            return False
        if streamlit_is_healthy(port):
            return True
        time.sleep(0.5)
    return False


def stop_child(process: Optional[subprocess.Popen], pid: int) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
            return
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            return
    if pid and is_current_project_streamlit(pid):
        terminate_process(pid)


def monitor_adopted_process(pid: int, port: int) -> bool:
    """监控启动器之外已经存在的当前项目进程。

    返回 True 表示收到主动停止请求，False 表示进程意外退出。
    """

    while process_is_alive(pid) and is_current_project_streamlit(pid):
        if STOP_REQUEST_PATH.exists():
            terminate_process(pid)
            return True
        time.sleep(1)
    return STOP_REQUEST_PATH.exists()


def supervise(port: int, python_executable: Path, adopt_pid: int = 0) -> int:
    ensure_runtime_directories()
    command = streamlit_command(python_executable, port)
    supervisor_pid = os.getpid()
    consecutive_restarts = 0

    if adopt_pid and is_current_project_streamlit(adopt_pid):
        status = build_status(
            adopt_pid,
            supervisor_pid,
            port,
            command,
            restart_count=0,
            state="running",
        )
        write_status(status)
        log_message(f"守护器已接管现有网页进程 PID={adopt_pid}。")
        if monitor_adopted_process(adopt_pid, port):
            STOP_REQUEST_PATH.unlink(missing_ok=True)
            remove_status()
            log_message("网页服务已按请求停止。")
            return 0
        consecutive_restarts = 1
        log_message("被接管的网页进程已退出，准备自动重启。")

    while consecutive_restarts <= MAX_RESTARTS:
        if STOP_REQUEST_PATH.exists():
            STOP_REQUEST_PATH.unlink(missing_ok=True)
            remove_status()
            log_message("网页服务在启动前收到停止请求。")
            return 0

        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt"
            else 0
        )
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=environment,
            creationflags=creationflags,
        )
        output_thread = threading.Thread(
            target=copy_process_output,
            args=(process,),
            daemon=True,
        )
        output_thread.start()

        status = build_status(
            process.pid,
            supervisor_pid,
            port,
            command,
            restart_count=consecutive_restarts,
        )
        write_status(status)
        log_message(
            f"正在启动 Streamlit，PID={process.pid}，端口={port}，"
            f"重启次数={consecutive_restarts}。"
        )

        if not wait_until_healthy(process, port):
            stop_requested = STOP_REQUEST_PATH.exists()
            stop_child(process, process.pid)
            if stop_requested:
                STOP_REQUEST_PATH.unlink(missing_ok=True)
                remove_status()
                log_message("网页服务已按请求停止。")
                return 0
            consecutive_restarts += 1
            log_message(
                f"Streamlit 未能在 {STARTUP_TIMEOUT_SECONDS} 秒内启动，"
                f"准备第 {consecutive_restarts} 次重启。"
            )
            continue

        status["state"] = "running"
        write_status(status)
        log_message(f"网页启动成功：http://localhost:{port}")
        running_since = time.monotonic()

        while process.poll() is None:
            if STOP_REQUEST_PATH.exists():
                stop_child(process, process.pid)
                STOP_REQUEST_PATH.unlink(missing_ok=True)
                remove_status()
                log_message("网页服务已按请求停止。")
                return 0
            if time.monotonic() - running_since >= STABLE_SECONDS:
                consecutive_restarts = 0
            time.sleep(1)

        exit_code = process.returncode
        consecutive_restarts += 1
        log_message(
            f"Streamlit 意外退出，退出码={exit_code}，"
            f"准备第 {consecutive_restarts} 次重启。"
        )

    failed_status = read_status() or {}
    failed_status.update(
        {
            "state": "failed",
            "last_error": (
                f"Streamlit 连续重启 {MAX_RESTARTS} 次仍失败，"
                "请检查日志。"
            ),
            "restart_count": MAX_RESTARTS,
        }
    )
    write_status(failed_status)
    log_message("连续重启达到上限，守护器停止。")
    return 1


def acquire_start_lock() -> bool:
    ensure_runtime_directories()
    for _ in range(30):
        try:
            descriptor = os.open(
                START_LOCK_PATH,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
                lock_file.write(f"{os.getpid()}\n{time.time()}\n")
            return True
        except FileExistsError:
            try:
                age = time.time() - START_LOCK_PATH.stat().st_mtime
            except OSError:
                age = 0
            if age > 60:
                START_LOCK_PATH.unlink(missing_ok=True)
                continue
            time.sleep(0.5)
    return False


def launch_supervisor(
    port: int,
    python_executable: Path,
    adopt_pid: int = 0,
) -> int:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--supervise",
        "--port",
        str(port),
        "--streamlit-python",
        str(python_executable),
    ]
    if adopt_pid:
        command.extend(["--adopt-pid", str(adopt_pid)])

    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    else:
        creationflags = 0

    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )
    return process.pid


def _scheduler_settings_enabled() -> bool:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.config import load_settings
    from src.database import get_email_settings

    settings = load_settings(send_email=False, require_api_key=False)
    values = get_email_settings(settings.database_path)
    return bool(
        values["email_enabled"] and values["auto_send_local_enabled"]
    )


def _read_scheduler_pid() -> int:
    if not SCHEDULER_STATUS_PATH.exists():
        return 0
    try:
        import json

        data = json.loads(SCHEDULER_STATUS_PATH.read_text(encoding="utf-8"))
        return int(data.get("pid", 0))
    except (OSError, TypeError, ValueError):
        return 0


def launch_scheduler_if_enabled(python_executable: Path) -> int:
    if not _scheduler_settings_enabled():
        return 0

    existing_pid = _read_scheduler_pid()
    if process_is_alive(existing_pid) and is_current_project_scheduler(
        existing_pid
    ):
        return existing_pid

    command = [
        str(python_executable),
        str(PROJECT_ROOT / "scripts" / "local_mail_scheduler.py"),
    ]
    creationflags = (
        getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt"
        else 0
    )
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        scheduler_pid = _read_scheduler_pid()
        if scheduler_pid == process.pid and process_is_alive(scheduler_pid):
            return scheduler_pid
        if process.poll() is not None:
            break
        time.sleep(0.25)
    return 0


def attach_scheduler_status(
    status: Dict[str, object],
    python_executable: Path,
) -> Dict[str, object]:
    scheduler_pid = launch_scheduler_if_enabled(python_executable)
    status["scheduler_pid"] = scheduler_pid
    status["scheduler_log_file"] = str(SCHEDULER_LOG_PATH.resolve())
    write_status(status)
    return status


def print_started(status: Dict[str, object], already_running: bool = False) -> None:
    if already_running:
        print(f"网页已经在运行：{status['url']}")
    print("====================================")
    print("每日热点新闻知识库已启动")
    print(f"访问地址：{status['url']}")
    print(f"日志文件：{display_relative_path(LOG_PATH)}")
    scheduler_pid = int(status.get("scheduler_pid", 0))
    if scheduler_pid:
        print(f"本地邮件调度器 PID：{scheduler_pid}")
        print(f"调度器日志：{display_relative_path(SCHEDULER_LOG_PATH)}")
    else:
        print("本地邮件调度器：未启用")
    print("停止服务：python scripts/stop_web.py")
    print("====================================")


def wait_for_supervisor(port: int, supervisor_pid: int) -> Optional[Dict[str, object]]:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS + 5
    while time.monotonic() < deadline:
        status = read_status()
        if status and int(status.get("supervisor_pid", 0)) == supervisor_pid:
            if status_is_running(status):
                return status
            if status.get("state") == "failed":
                return None
        if not process_is_alive(supervisor_pid):
            return None
        time.sleep(0.5)
    return None


def start() -> int:
    ensure_runtime_directories()
    if not APP_PATH.exists():
        print(f"启动失败：未找到 {APP_PATH}。")
        print("请确认当前项目文件完整，并在项目根目录运行命令。")
        return 1

    python_executable = find_streamlit_python()
    if python_executable is None:
        print("启动失败：当前环境和项目 .venv 中都没有可用的 Streamlit。")
        print("请先运行：pip install -r requirements.txt")
        return 1

    if not acquire_start_lock():
        print("另一个启动操作正在进行，请稍等后运行：")
        print("python scripts/status_web.py")
        return 1

    try:
        STOP_REQUEST_PATH.unlink(missing_ok=True)
        status = read_status()
        if status_is_running(status):
            supervisor_pid = int(status.get("supervisor_pid", 0))
            if process_is_alive(supervisor_pid):
                status = attach_scheduler_status(status, python_executable)
                print_started(status, already_running=True)
                return 0

            # 网页仍在运行但守护器已退出，重新建立守护而不重复启动网页。
            supervisor_pid = launch_supervisor(
                int(status["port"]),
                python_executable,
                adopt_pid=int(status["pid"]),
            )
            adopted_status = wait_for_supervisor(
                int(status["port"]),
                supervisor_pid,
            )
            if adopted_status:
                adopted_status = attach_scheduler_status(
                    adopted_status, python_executable
                )
                print_started(adopted_status, already_running=True)
                return 0

        remove_status()

        existing = find_existing_project_service()
        if existing:
            command = streamlit_command(
                python_executable,
                int(existing["port"]),
            )
            provisional_status = build_status(
                int(existing["pid"]),
                0,
                int(existing["port"]),
                command,
                restart_count=0,
                state="running",
            )
            write_status(provisional_status)
            supervisor_pid = launch_supervisor(
                int(existing["port"]),
                python_executable,
                adopt_pid=int(existing["pid"]),
            )
            adopted_status = wait_for_supervisor(
                int(existing["port"]),
                supervisor_pid,
            )
            if adopted_status:
                adopted_status = attach_scheduler_status(
                    adopted_status, python_executable
                )
                print_started(adopted_status, already_running=True)
                return 0

        port = find_available_port(DEFAULT_PORT)
        if port != DEFAULT_PORT:
            print(
                f"端口 {DEFAULT_PORT} 已被其他程序占用，"
                f"将自动使用端口 {port}。"
            )

        supervisor_pid = launch_supervisor(port, python_executable)
        running_status = wait_for_supervisor(port, supervisor_pid)
        if running_status:
            running_status = attach_scheduler_status(
                running_status, python_executable
            )
            print_started(running_status)
            return 0

        print("网页启动失败，请查看日志：")
        print(display_relative_path(LOG_PATH))
        return 1
    finally:
        START_LOCK_PATH.unlink(missing_ok=True)


def main() -> None:
    args = parse_args()
    if args.supervise:
        if not args.port or not args.streamlit_python:
            raise SystemExit(2)
        raise SystemExit(
            supervise(
                args.port,
                Path(args.streamlit_python),
                adopt_pid=args.adopt_pid,
            )
        )
    raise SystemExit(start())


if __name__ == "__main__":
    main()
