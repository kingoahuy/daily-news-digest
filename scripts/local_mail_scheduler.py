import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
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


def write_scheduler_status(
    state: str,
    message: str = "",
    details: dict[str, object] | None = None,
) -> None:
    data = {
        "pid": os.getpid(),
        "state": state,
        "started_at": utc_now_text(),
        "checked_at": utc_now_text(),
        "project_root": str(PROJECT_ROOT.resolve()),
        "log_file": str(SCHEDULER_LOG_PATH.resolve()),
        "message": message,
    }
    if details:
        data.update(details)
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


def _parse_hhmm(value: object) -> tuple[int, int]:
    text = str(value).strip()
    parts = text.split(":")
    if (
        len(parts) != 2
        or any(len(part) != 2 or not part.isdigit() for part in parts)
        or not 0 <= int(parts[0]) <= 23
        or not 0 <= int(parts[1]) <= 59
    ):
        raise ValueError(f"发送时间无效：{text}")
    return int(parts[0]), int(parts[1])


def _minutes_text(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} 分钟"
    hours, rest = divmod(minutes, 60)
    return f"{hours} 小时 {rest} 分钟" if rest else f"{hours} 小时"


def run_send_command(
    db_path: Path,
    run_date: str,
    scheduled_time: str,
    actual_time: str,
) -> bool:
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
            actual_time,
            db_path,
        )
        log("本地定时邮件发送成功。")
        return True

    record_scheduler_run(
        run_date,
        scheduled_time,
        "failed",
        summary,
        actual_time,
        db_path,
    )
    log(f"本地定时邮件发送失败，退出码={completed.returncode}。")
    return False


def _base_result(
    status: str,
    message: str,
    **details: object,
) -> dict[str, object]:
    return {
        "status": status,
        "message": message,
        **details,
    }


def check_once(db_path: Path) -> dict[str, object]:
    values = get_email_settings(db_path)
    enabled = bool(values["email_enabled"])
    auto_enabled = bool(values["auto_send_local_enabled"])
    scheduled_time = str(values["email_send_time"])
    grace_minutes = int(values.get("send_grace_minutes") or 180)
    if not values["email_enabled"]:
        return _base_result(
            "skipped",
            "邮件推送开关未启用。",
            email_enabled=enabled,
            auto_send_local_enabled=auto_enabled,
            scheduled_time=scheduled_time,
            send_grace_minutes=grace_minutes,
        )
    if not values["auto_send_local_enabled"]:
        return _base_result(
            "skipped",
            "本地自动发送开关未启用。",
            email_enabled=enabled,
            auto_send_local_enabled=auto_enabled,
            scheduled_time=scheduled_time,
            send_grace_minutes=grace_minutes,
        )

    timezone_name = str(values["timezone"])
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return _base_result(
            "failed",
            f"时区无效：{timezone_name}",
            email_enabled=enabled,
            auto_send_local_enabled=auto_enabled,
            scheduled_time=scheduled_time,
            send_grace_minutes=grace_minutes,
        )

    now = datetime.now(zone)
    run_date = now.date().isoformat()
    actual_time = now.strftime("%H:%M")
    try:
        hour, minute = _parse_hhmm(scheduled_time)
    except ValueError as exc:
        return _base_result(
            "failed",
            str(exc),
            email_enabled=enabled,
            auto_send_local_enabled=auto_enabled,
            timezone=timezone_name,
            current_time=actual_time,
            run_date=run_date,
            scheduled_time=scheduled_time,
            send_grace_minutes=grace_minutes,
        )

    scheduled_at = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    grace_until = scheduled_at + timedelta(minutes=grace_minutes)
    common = {
        "email_enabled": enabled,
        "auto_send_local_enabled": auto_enabled,
        "timezone": timezone_name,
        "run_date": run_date,
        "current_time": actual_time,
        "scheduled_time": scheduled_time,
        "send_grace_minutes": grace_minutes,
        "grace_until": grace_until.strftime("%H:%M"),
    }

    if scheduler_has_success(run_date, db_path=db_path):
        message = f"{run_date} 已成功发送过，跳过重复任务。"
        return _base_result(
            "skipped",
            message,
            already_sent=True,
            **common,
        )

    if now < scheduled_at:
        seconds = int((scheduled_at - now).total_seconds())
        minutes_left = max(1, (seconds + 59) // 60)
        message = (
            f"当前时间 {actual_time}，计划时间 {scheduled_time}，"
            f"距离发送还有 {_minutes_text(minutes_left)}。"
        )
        return _base_result(
            "pending",
            message,
            already_sent=False,
            minutes_until_send=minutes_left,
            **common,
        )

    if now > grace_until:
        message = (
            f"今天已超过计划发送时间超过 {grace_minutes} 分钟，"
            "为避免过晚打扰，已跳过。可以手动发送。"
        )
        record_scheduler_run(
            run_date,
            scheduled_time,
            "skipped",
            message,
            actual_time,
            db_path,
        )
        return _base_result(
            "skipped",
            message,
            already_sent=False,
            **common,
        )

    message = (
        f"当前时间 {actual_time} 已到达计划时间 {scheduled_time}，"
        f"且仍在 {grace_minutes} 分钟宽限期内，准备发送。"
    )
    log(message)
    sent = run_send_command(db_path, run_date, scheduled_time, actual_time)
    status = "success" if sent else "failed"
    return _base_result(
        status,
        f"{message} 结果：{'成功' if sent else '失败'}。",
        already_sent=False,
        **common,
    )


def format_result(result: dict[str, object]) -> str:
    lines = [
        f"当前时间：{result.get('current_time', '未知')}",
        f"计划时间：{result.get('scheduled_time', '未知')}",
        f"邮件推送：{'启用' if result.get('email_enabled') else '未启用'}",
        (
            "本地自动发送："
            f"{'启用' if result.get('auto_send_local_enabled') else '未启用'}"
        ),
        f"补发宽限：{result.get('send_grace_minutes', 180)} 分钟",
        f"当天已成功发送：{'是' if result.get('already_sent') else '否'}",
        f"状态：{result.get('status')}",
        f"结果：{result.get('message')}",
        f"日志：{SCHEDULER_LOG_PATH}",
    ]
    return "\n".join(lines)


def run_scheduler(interval: int, once: bool) -> int:
    if not once and not ensure_single_instance():
        return 0

    settings = load_settings(send_email=False, require_api_key=False)
    db_path = settings.database_path
    ensure_runtime_directories()
    if not once:
        write_scheduler_status("running", "调度器已启动，等待下一次检查。")
        log(f"本地邮件调度器启动，检查间隔={interval} 秒。")
    try:
        while True:
            result = check_once(db_path)
            message = str(result.get("message") or "")
            if once:
                print(format_result(result))
                return 0
            write_scheduler_status(
                "running" if result.get("status") != "failed" else "failed",
                message,
                result,
            )
            time.sleep(max(10, interval))
    except KeyboardInterrupt:
        log("本地邮件调度器收到停止请求。")
        return 0
    except Exception as exc:
        message = f"调度器异常：{type(exc).__name__}"
        write_scheduler_status("failed", message)
        log(message)
        return 1


if __name__ == "__main__":
    arguments = parse_args()
    raise SystemExit(run_scheduler(arguments.interval, arguments.once))
