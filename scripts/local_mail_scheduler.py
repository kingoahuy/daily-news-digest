import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from web_runtime import (
    PROJECT_ROOT,
    SCHEDULER_LOG_PATH,
    SCHEDULER_STATUS_PATH,
    ensure_runtime_directories,
    is_current_project_scheduler,
    process_is_alive,
    utc_now_text,
)


sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_settings
from src.database import (
    get_email_settings,
    record_scheduler_run,
    scheduler_has_success,
)


SENSITIVE_ENV_NAMES = (
    "DEEPSEEK_API_KEY",
    "SMTP_PASSWORD",
    "SMTP_USER",
    "MAIL_FROM",
    "MAIL_TO",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="根据网页设置执行本地每日邮件发送。"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只检查一次设置和时间，用于测试。",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def sensitive_values() -> list[str]:
    values = []
    env_values = {}
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                env_values[name.strip()] = value.strip().strip("\"'")
        except OSError:
            pass
    for name in SENSITIVE_ENV_NAMES:
        value = os.environ.get(name, "") or env_values.get(name, "")
        if value and len(value) >= 4:
            values.append(value)
    return values


SENSITIVE_VALUES = sensitive_values()


def redact(text: str) -> str:
    safe_text = text
    for value in SENSITIVE_VALUES:
        safe_text = safe_text.replace(value, "<SENSITIVE_VALUE_REDACTED>")
    return re.sub(
        r"(?i)(api[_-]?key|smtp[_-]?password|authorization)"
        r"(\s*[=:]\s*)[^\s,;]+",
        r"\1\2<REDACTED>",
        safe_text,
    )


def log(message: str) -> None:
    ensure_runtime_directories()
    with SCHEDULER_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{utc_now_text()}] {redact(message)}\n")


def read_scheduler_status():
    if not SCHEDULER_STATUS_PATH.exists():
        return None
    try:
        data = json.loads(SCHEDULER_STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_scheduler_status(state: str, message: str = "") -> None:
    data = {
        "pid": os.getpid(),
        "state": state,
        "started_at": utc_now_text(),
        "project_root": str(PROJECT_ROOT.resolve()),
        "log_file": str(SCHEDULER_LOG_PATH.resolve()),
        "message": message,
    }
    temporary = SCHEDULER_STATUS_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(SCHEDULER_STATUS_PATH)


def ensure_single_instance() -> bool:
    status = read_scheduler_status()
    if not status:
        return True
    pid = status.get("pid")
    if process_is_alive(pid) and is_current_project_scheduler(pid):
        print(f"本地邮件调度器已经在运行，PID：{pid}")
        return False
    SCHEDULER_STATUS_PATH.unlink(missing_ok=True)
    return True


def run_send_command(db_path: Path, run_date: str, scheduled_time: str) -> bool:
    log(f"到达计划时间 {scheduled_time}，开始生成并发送日报。")
    completed = subprocess.run(
        [sys.executable, "-m", "src.main", "--send"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    output = redact((completed.stdout + completed.stderr).strip())
    summary = output[-800:] if output else f"退出码 {completed.returncode}"
    if completed.returncode == 0:
        record_scheduler_run(
            run_date,
            scheduled_time,
            "success",
            summary,
            db_path,
        )
        log("本地定时邮件发送成功。")
        return True

    record_scheduler_run(
        run_date,
        scheduled_time,
        "failed",
        summary,
        db_path,
    )
    log(f"本地定时邮件发送失败，退出码={completed.returncode}。")
    return False


def check_once(db_path: Path) -> str:
    values = get_email_settings(db_path)
    if not values["email_enabled"]:
        return "邮件推送开关未启用。"
    if not values["auto_send_local_enabled"]:
        return "本地自动发送开关未启用。"

    timezone_name = str(values["timezone"])
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return f"时区无效：{timezone_name}"

    now = datetime.now(zone)
    run_date = now.date().isoformat()
    current_time = now.strftime("%H:%M")
    scheduled_time = str(values["email_send_time"])
    if current_time != scheduled_time:
        return f"当前时间 {current_time}，计划时间 {scheduled_time}，无需发送。"
    if scheduler_has_success(run_date, scheduled_time, db_path):
        return f"{run_date} 已成功发送过，跳过重复任务。"

    run_send_command(db_path, run_date, scheduled_time)
    return f"已执行 {run_date} {scheduled_time} 的发送任务。"


def run_scheduler(interval: int, once: bool) -> int:
    if not ensure_single_instance():
        return 0

    settings = load_settings(send_email=False, require_api_key=False)
    db_path = settings.database_path
    ensure_runtime_directories()
    write_scheduler_status("running")
    log(f"本地邮件调度器启动，检查间隔={interval} 秒。")
    try:
        while True:
            message = check_once(db_path)
            write_scheduler_status("running", message)
            if once:
                print(message)
                return 0
            time.sleep(max(10, interval))
    except KeyboardInterrupt:
        log("本地邮件调度器收到停止请求。")
        return 0
    except Exception as exc:
        message = f"调度器异常：{type(exc).__name__}"
        write_scheduler_status("failed", message)
        log(message)
        return 1
    finally:
        if once:
            SCHEDULER_STATUS_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    arguments = parse_args()
    raise SystemExit(run_scheduler(arguments.interval, arguments.once))
