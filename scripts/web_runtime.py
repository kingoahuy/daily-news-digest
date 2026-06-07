import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
LOGS_DIR = PROJECT_ROOT / "logs"
STATUS_PATH = RUNTIME_DIR / "web_status.json"
STOP_REQUEST_PATH = RUNTIME_DIR / "web_stop.request"
START_LOCK_PATH = RUNTIME_DIR / "web_start.lock"
LOG_PATH = LOGS_DIR / "streamlit_web.log"
SCHEDULER_STATUS_PATH = RUNTIME_DIR / "mail_scheduler_status.json"
SCHEDULER_LOG_PATH = LOGS_DIR / "local_mail_scheduler.log"
DEFAULT_PORT = 8501
MAX_PORT = 8599


def ensure_runtime_directories() -> None:
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
    ensure_runtime_directories()
    temporary_path = STATUS_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(STATUS_PATH)


def remove_status() -> None:
    STATUS_PATH.unlink(missing_ok=True)


def process_is_alive(pid: object) -> bool:
    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return False
    if process_id <= 0:
        return False

    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process_id}", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return str(process_id) in result.stdout

    try:
        os.kill(process_id, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def get_process_command_line(pid: object) -> str:
    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return ""

    if os.name == "nt":
        command = (
            "$p=Get-CimInstance Win32_Process -Filter "
            f"'ProcessId={process_id}' -ErrorAction SilentlyContinue;"
            "if($p){[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
            "$p.CommandLine}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return result.stdout.strip()

    command_path = Path(f"/proc/{process_id}/cmdline")
    try:
        return command_path.read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        )
    except OSError:
        return ""


def is_current_project_streamlit(pid: object) -> bool:
    command_line = get_process_command_line(pid).casefold()
    app_path = str(APP_PATH.resolve()).casefold()
    normalized_command = command_line.replace("\\", "/")
    normalized_app = app_path.replace("\\", "/")
    return (
        "streamlit" in command_line
        and normalized_app in normalized_command
        and "run" in command_line
    )


def is_current_project_supervisor(pid: object) -> bool:
    command_line = get_process_command_line(pid).casefold().replace("\\", "/")
    script_path = str(
        (PROJECT_ROOT / "scripts" / "start_web.py").resolve()
    ).casefold().replace("\\", "/")
    return script_path in command_line and "--supervise" in command_line


def is_current_project_scheduler(pid: object) -> bool:
    command_line = get_process_command_line(pid).casefold().replace("\\", "/")
    script_path = str(
        (PROJECT_ROOT / "scripts" / "local_mail_scheduler.py").resolve()
    ).casefold().replace("\\", "/")
    return script_path in command_line


def port_is_open(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def port_is_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", int(port)))
        return True
    except OSError:
        return False


def streamlit_is_healthy(port: int, timeout: float = 1.0) -> bool:
    try:
        with urlopen(
            f"http://127.0.0.1:{int(port)}/_stcore/health",
            timeout=timeout,
        ) as response:
            body = response.read(64).decode("utf-8", errors="replace").lower()
            return response.status == 200 and "ok" in body
    except (OSError, URLError, ValueError):
        return False


def listening_pids(port: int) -> Iterable[int]:
    if os.name != "nt":
        return []

    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    pids = set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP":
            continue
        local_address = fields[1]
        state = fields[3].upper()
        if state != "LISTENING":
            continue
        try:
            local_port = int(local_address.rsplit(":", 1)[1])
            process_id = int(fields[4])
        except (ValueError, IndexError):
            continue
        if local_port == int(port):
            pids.add(process_id)
    return sorted(pids)


def find_existing_project_service() -> Optional[Dict[str, object]]:
    for port in range(DEFAULT_PORT, MAX_PORT + 1):
        if not port_is_open(port, timeout=0.05):
            continue
        for pid in listening_pids(port):
            if is_current_project_streamlit(pid):
                return {
                    "pid": pid,
                    "port": port,
                    "url": f"http://localhost:{port}",
                }
    return None


def status_is_running(status: Optional[Dict[str, object]]) -> bool:
    if not status:
        return False
    if Path(str(status.get("project_root", ""))).resolve() != PROJECT_ROOT:
        return False
    try:
        pid = int(status["pid"])
        port = int(status["port"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        process_is_alive(pid)
        and is_current_project_streamlit(pid)
        and port_is_open(port)
        and streamlit_is_healthy(port)
    )


def find_available_port(start_port: int = DEFAULT_PORT) -> int:
    for port in range(start_port, MAX_PORT + 1):
        if port_is_available(port):
            return port
    raise RuntimeError(
        f"{start_port}-{MAX_PORT} 端口均被占用，请关闭不需要的本地服务后重试。"
    )


def find_streamlit_python() -> Optional[Path]:
    candidates = []
    if os.environ.get("VIRTUAL_ENV"):
        candidates.append(Path(sys.executable))

    if os.name == "nt":
        candidates.append(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe")
    else:
        candidates.append(PROJECT_ROOT / ".venv" / "bin" / "python")
    candidates.append(Path(sys.executable))

    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        result = subprocess.run(
            [str(resolved), "-c", "import streamlit"],
            capture_output=True,
            text=True,
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if os.name == "nt"
                else 0
            ),
            check=False,
        )
        if result.returncode == 0:
            return resolved
    return None


def terminate_process(pid: object) -> bool:
    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return False
    if not process_is_alive(process_id):
        return True

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(process_id), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return result.returncode == 0 or not process_is_alive(process_id)

    try:
        os.kill(process_id, 15)
    except OSError:
        return False
    for _ in range(30):
        if not process_is_alive(process_id):
            return True
        time.sleep(0.1)
    return False


def display_relative_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)
