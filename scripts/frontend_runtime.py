import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from urllib.error import URLError
from urllib.request import urlopen

from web_runtime import get_process_command_line, process_is_alive, terminate_process


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "web"
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
LOGS_DIR = PROJECT_ROOT / "logs"
STATUS_PATH = RUNTIME_DIR / "frontend_status.json"
STOP_REQUEST_PATH = RUNTIME_DIR / "frontend_stop.request"
START_LOCK_PATH = RUNTIME_DIR / "frontend_start.lock"
LOG_PATH = LOGS_DIR / "next_frontend.log"
DEFAULT_PORT = 3000
MAX_PORT = 3099


def ensure_directories() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_status() -> Optional[Dict[str, object]]:
    if not STATUS_PATH.exists():
        return None
    try:
        data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_status(data: Dict[str, object]) -> None:
    ensure_directories()
    temporary = STATUS_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATUS_PATH)


def remove_status() -> None:
    STATUS_PATH.unlink(missing_ok=True)


def port_is_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", int(port)))
        return True
    except OSError:
        return False


def find_available_port() -> int:
    for port in range(DEFAULT_PORT, MAX_PORT + 1):
        if port_is_available(port):
            return port
    raise RuntimeError(f"{DEFAULT_PORT}-{MAX_PORT} 端口均被占用。")


def frontend_is_healthy(port: int, timeout: float = 1.5) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}", timeout=timeout) as response:
            return response.status == 200
    except (OSError, URLError, ValueError):
        return False


def is_current_frontend(pid: object) -> bool:
    command = get_process_command_line(pid).casefold().replace("\\", "/")
    next_bin = str(
        (FRONTEND_ROOT / "node_modules" / "next" / "dist" / "bin" / "next")
        .resolve()
    ).casefold().replace("\\", "/")
    return next_bin in command and " start " in f" {command} "


def is_current_supervisor(pid: object) -> bool:
    command = get_process_command_line(pid).casefold().replace("\\", "/")
    script = str(
        (PROJECT_ROOT / "scripts" / "start_frontend.py").resolve()
    ).casefold().replace("\\", "/")
    return script in command and "--supervise" in command


def status_is_running(status: Optional[Dict[str, object]]) -> bool:
    if not status:
        return False
    if str(status.get("project_root", "")) != str(PROJECT_ROOT.resolve()):
        return False
    try:
        pid = int(status["pid"])
        port = int(status["port"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        process_is_alive(pid)
        and is_current_frontend(pid)
        and frontend_is_healthy(port)
    )


def node_executable() -> Optional[Path]:
    result = subprocess.run(
        ["where.exe", "node"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        return None
    first = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    return Path(first) if first else None


def npm_executable() -> Optional[Path]:
    result = subprocess.run(
        ["where.exe", "npm.cmd"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        return None
    first = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    return Path(first) if first else None


def needs_build() -> bool:
    build_id = FRONTEND_ROOT / ".next" / "BUILD_ID"
    if not build_id.exists():
        return True
    build_time = build_id.stat().st_mtime
    watched = [
        FRONTEND_ROOT / "package.json",
        FRONTEND_ROOT / "package-lock.json",
        FRONTEND_ROOT / "next.config.ts",
    ]
    watched.extend((FRONTEND_ROOT / "src").rglob("*"))
    return any(
        path.is_file() and path.stat().st_mtime > build_time
        for path in watched
    )


def log_message(message: str) -> None:
    ensure_directories()
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{utc_now_text()}] {message}\n")


def run_logged(command: list[str], timeout: int) -> bool:
    ensure_directories()
    completed = subprocess.run(
        command,
        cwd=FRONTEND_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        if completed.stdout:
            log_file.write(completed.stdout)
        if completed.stderr:
            log_file.write(completed.stderr)
    return completed.returncode == 0


def ensure_frontend_ready() -> bool:
    npm = npm_executable()
    if npm is None:
        print("Next.js 启动失败：未找到 npm.cmd。")
        return False
    if not (FRONTEND_ROOT / "node_modules").exists():
        print("正在安装 Next.js 前端依赖...")
        if not run_logged([str(npm), "install"], timeout=900):
            print("前端依赖安装失败，请查看 logs/next_frontend.log。")
            return False
    if needs_build():
        print("正在构建 Next.js 前端...")
        if not run_logged([str(npm), "run", "build"], timeout=900):
            print("前端构建失败，请查看 logs/next_frontend.log。")
            return False
    return True


def stop_process(pid: int) -> None:
    if process_is_alive(pid) and is_current_frontend(pid):
        terminate_process(pid)
