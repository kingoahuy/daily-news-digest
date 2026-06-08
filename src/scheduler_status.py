import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.config import PROJECT_ROOT
from src.database import (
    DEFAULT_DB_PATH,
    get_email_settings,
    get_latest_scheduler_run,
    scheduler_has_success,
)


RUNTIME_DIR = PROJECT_ROOT / ".runtime"
SCHEDULER_STATUS_PATH = RUNTIME_DIR / "mail_scheduler_status.json"
SCHEDULER_LOG_PATH = PROJECT_ROOT / "logs" / "local_mail_scheduler.log"


def _read_status_file() -> Dict[str, object]:
    if not SCHEDULER_STATUS_PATH.exists():
        return {}
    try:
        data = json.loads(SCHEDULER_STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _process_is_alive(pid: object) -> bool:
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


def _process_command_line(pid: object) -> str:
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
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return completed.stdout.strip()

    path = Path(f"/proc/{process_id}/cmdline")
    try:
        return path.read_bytes().replace(b"\0", b" ").decode(
            "utf-8",
            errors="replace",
        )
    except OSError:
        return ""


def _is_scheduler_process(pid: object) -> bool:
    command = _process_command_line(pid).casefold().replace("\\", "/")
    script = str(
        (PROJECT_ROOT / "scripts" / "local_mail_scheduler.py").resolve()
    ).casefold().replace("\\", "/")
    return script in command


def _safe_now(timezone_name: str) -> Optional[datetime]:
    try:
        return datetime.now(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        return None


def scheduler_status_payload(
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    email = get_email_settings(db_path)
    timezone_name = str(email["timezone"])
    now = _safe_now(timezone_name)
    run_date = now.date().isoformat() if now else ""
    current_time = now.strftime("%H:%M") if now else ""
    sent_today = scheduler_has_success(run_date, db_path=db_path) if run_date else False

    status_file = _read_status_file()
    pid = int(status_file.get("pid") or 0)
    running = _process_is_alive(pid) and _is_scheduler_process(pid)
    latest_run = get_latest_scheduler_run(db_path)

    warning = ""
    if bool(email["email_enabled"]) and bool(email["auto_send_local_enabled"]):
        if not running:
            warning = "已启用本地自动发送，但未检测到本地邮件调度器运行。"
        elif now and not sent_today:
            scheduled_time = str(email["email_send_time"])
            if current_time >= scheduled_time:
                warning = (
                    "今天已经超过计划发送时间，但未检测到成功发送记录。"
                    "请检查调度器日志，或在历史日报中心手动发送。"
                )

    return {
        "email_enabled": bool(email["email_enabled"]),
        "auto_send_local_enabled": bool(email["auto_send_local_enabled"]),
        "send_grace_minutes": int(email["send_grace_minutes"]),
        "timezone": timezone_name,
        "current_time": current_time,
        "scheduled_time": str(email["email_send_time"]),
        "today": run_date,
        "sent_today": sent_today,
        "running": running,
        "pid": pid if running else 0,
        "state": str(status_file.get("state") or "stopped"),
        "message": str(status_file.get("message") or ""),
        "checked_at": str(status_file.get("checked_at") or ""),
        "started_at": str(status_file.get("started_at") or ""),
        "log_file": str(SCHEDULER_LOG_PATH.resolve()),
        "latest_run": dict(latest_run) if latest_run else None,
        "warning": warning,
    }
