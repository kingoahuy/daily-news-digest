import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from urllib.error import URLError
from urllib.request import urlopen

from web_runtime import get_process_command_line, process_is_alive, terminate_process


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
LOGS_DIR = PROJECT_ROOT / "logs"
STATUS_PATH = RUNTIME_DIR / "api_status.json"
STOP_REQUEST_PATH = RUNTIME_DIR / "api_stop.request"
START_LOCK_PATH = RUNTIME_DIR / "api_start.lock"
LOG_PATH = LOGS_DIR / "api_backend.log"
DEFAULT_PORT = 8000
MAX_PORT = 8002


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
    raise RuntimeError("8000、8001、8002 端口均被占用。")


def api_is_healthy(port: int, timeout: float = 1.5) -> bool:
    try:
        with urlopen(
            f"http://127.0.0.1:{port}/api/health",
            timeout=timeout,
        ) as response:
            return response.status == 200
    except (OSError, URLError, ValueError):
        return False


def is_current_api(pid: object) -> bool:
    command = get_process_command_line(pid).casefold().replace("\\", "/")
    return (
        "-m uvicorn" in command
        and "src.api:app" in command
        and str(PROJECT_ROOT.resolve()).casefold().replace("\\", "/")
        in command
    )


def is_current_supervisor(pid: object) -> bool:
    command = get_process_command_line(pid).casefold().replace("\\", "/")
    script = str(
        (PROJECT_ROOT / "scripts" / "start_api.py").resolve()
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
    return process_is_alive(pid) and is_current_api(pid) and api_is_healthy(port)


def stop_process(pid: int) -> None:
    if process_is_alive(pid) and is_current_api(pid):
        terminate_process(pid)
