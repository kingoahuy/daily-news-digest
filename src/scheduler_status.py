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
    get_report_by_date,
    scheduler_has_success,
)


RUNTIME_DIR = PROJECT_ROOT / ".runtime"
SCHEDULER_STATUS_PATH = RUNTIME_DIR / "mail_scheduler_status.json"
SCHEDULER_LOG_PATH = PROJECT_ROOT / "logs" / "local_mail_scheduler.log"
GENERATION_TIME = "07:30"


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
    report = get_report_by_date(run_date, db_path) if run_date else None
    generated_today = report is not None
    sent_by_report = bool(report and report.get("email_sent"))
    sent_by_scheduler = (
        scheduler_has_success(
            run_date,
            scheduled_time=str(email["email_send_time"]),
            task_type="email",
            db_path=db_path,
        )
        if run_date
        else False
    )
    sent_today = sent_by_report or sent_by_scheduler

    status_file = _read_status_file()
    pid = int(status_file.get("pid") or 0)
    running = _process_is_alive(pid) and _is_scheduler_process(pid)
    latest_run = get_latest_scheduler_run(db_path=db_path)
    latest_generation_run = get_latest_scheduler_run(
        db_path=db_path,
        task_type="generate",
    )
    latest_email_run = get_latest_scheduler_run(
        db_path=db_path,
        task_type="email",
    )

    latest_generation_failed = (
        latest_generation_run
        and str(latest_generation_run.get("run_date")) == run_date
        and str(latest_generation_run.get("status")) == "failed"
    )
    latest_email_failed = (
        latest_email_run
        and str(latest_email_run.get("run_date")) == run_date
        and str(latest_email_run.get("status")) == "failed"
    )

    warning = ""
    if latest_generation_failed and not generated_today:
        warning = (
            "今日日报自动生成失败，请查看本地调度器日志，"
            "也可以在首页点击“立即生成今日日报”。"
        )
    elif now and not generated_today and current_time >= GENERATION_TIME and not running:
        warning = (
            "今天还没有生成日报，可手动生成。"
            "本地 07:30 自动生成依赖本机网页/调度器运行。"
        )
    elif bool(email["email_enabled"]) and bool(email["auto_send_local_enabled"]):
        if not running:
            warning = (
                "已启用本地自动发送，但未检测到本地调度器运行。"
                "07:30 自动生成和按时邮件都依赖它。"
            )
        elif latest_email_failed:
            warning = (
                "今天自动邮件发送失败，请查看本地调度器日志，"
                "可在设置页点击“立即发送今天日报”。"
            )
        elif now and not sent_today and current_time >= str(email["email_send_time"]):
            warning = (
                "今天已经超过计划发送时间，但未检测到成功发送记录。"
                "请检查调度器日志，或在设置页手动发送今日日报。"
            )

    return {
        "email_enabled": bool(email["email_enabled"]),
        "auto_send_local_enabled": bool(email["auto_send_local_enabled"]),
        "send_grace_minutes": int(email["send_grace_minutes"]),
        "timezone": timezone_name,
        "current_time": current_time,
        "scheduled_time": str(email["email_send_time"]),
        "generation_time": GENERATION_TIME,
        "today": run_date,
        "generated_today": generated_today,
        "sent_today": sent_today,
        "running": running,
        "pid": pid if running else 0,
        "state": str(status_file.get("state") or "stopped"),
        "message": str(status_file.get("message") or ""),
        "checked_at": str(status_file.get("checked_at") or ""),
        "started_at": str(status_file.get("started_at") or ""),
        "log_file": str(SCHEDULER_LOG_PATH.resolve()),
        "latest_run": dict(latest_run) if latest_run else None,
        "latest_generation_run": (
            dict(latest_generation_run) if latest_generation_run else None
        ),
        "latest_email_run": dict(latest_email_run) if latest_email_run else None,
        "warning": warning,
    }
