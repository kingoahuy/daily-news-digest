import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

from web_runtime import (
    PROJECT_ROOT,
    SCHEDULER_LOG_PATH,
    SCHEDULER_STATUS_PATH,
    ensure_runtime_directories,
    is_current_project_scheduler,
    process_is_alive,
    terminate_process,
)


def _read_scheduler_pid() -> int:
    if not SCHEDULER_STATUS_PATH.exists():
        return 0
    try:
        data = json.loads(SCHEDULER_STATUS_PATH.read_text(encoding="utf-8"))
        return int(data.get("pid", 0))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return 0


def scheduler_settings_reason() -> Tuple[bool, str]:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.config import load_settings
    from src.database import get_email_settings

    settings = load_settings(send_email=False, require_api_key=False)
    values = get_email_settings(settings.database_path)
    if not bool(values["email_enabled"]):
        return False, "email_enabled=false"
    if not bool(values["auto_send_local_enabled"]):
        return False, "auto_send_local_enabled=false"
    return True, "email_enabled=true, auto_send_local_enabled=true"


def launch_scheduler_if_enabled(
    python_executable: Path | None = None,
) -> Tuple[int, str]:
    ensure_runtime_directories()
    enabled, reason = scheduler_settings_reason()
    if not enabled:
        return 0, reason

    existing_pid = _read_scheduler_pid()
    if process_is_alive(existing_pid) and is_current_project_scheduler(
        existing_pid
    ):
        return existing_pid, "already_running"

    command = [
        str(python_executable or Path(sys.executable)),
        str(PROJECT_ROOT / "scripts" / "local_mail_scheduler.py"),
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
            if sys.platform.startswith("win")
            else 0
        ),
        start_new_session=not sys.platform.startswith("win"),
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        scheduler_pid = _read_scheduler_pid()
        if scheduler_pid == process.pid and process_is_alive(scheduler_pid):
            return scheduler_pid, "started"
        if process.poll() is not None:
            break
        time.sleep(0.25)
    return 0, "start_failed"


def stop_scheduler() -> bool:
    scheduler_pid = _read_scheduler_pid()
    stopped = False
    if process_is_alive(scheduler_pid) and is_current_project_scheduler(
        scheduler_pid
    ):
        stopped = terminate_process(scheduler_pid)
    SCHEDULER_STATUS_PATH.unlink(missing_ok=True)
    return stopped


def scheduler_status_summary(pid: int, reason: str) -> Dict[str, object]:
    return {
        "scheduler_pid": int(pid),
        "scheduler_reason": reason,
        "scheduler_log_file": str(SCHEDULER_LOG_PATH.resolve()),
    }
