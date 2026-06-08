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
    get_latest_scheduler_run,
    get_report_by_date,
    record_scheduler_run,
    scheduler_has_success,
)
from src.report_delivery import ReportDeliveryError, deliver_stored_report


GENERATION_TIME = "07:30"
SENSITIVE_ENV_NAMES = (
    "DEEPSEEK_API_KEY",
    "SMTP_PASSWORD",
    "SMTP_USER",
    "MAIL_FROM",
    "MAIL_TO",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local scheduler for daily generation and optional email delivery."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check generation/email rules once and exit.",
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
        print(f"本地调度器已经在运行，PID：{pid}")
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
        raise ValueError(f"时间无效：{text}")
    return int(parts[0]), int(parts[1])


def _time_at(now: datetime, hhmm: str) -> datetime:
    hour, minute = _parse_hhmm(hhmm)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _minutes_text(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} 分钟"
    hours, rest = divmod(minutes, 60)
    return f"{hours} 小时 {rest} 分钟" if rest else f"{hours} 小时"


def _latest_task_run(
    db_path: Path,
    task_type: str,
) -> dict[str, object] | None:
    return get_latest_scheduler_run(db_path=db_path, task_type=task_type)


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


def _command_summary(completed: subprocess.CompletedProcess[str]) -> str:
    output = redact((completed.stdout + completed.stderr).strip())
    return output[-1000:] if output else f"退出码 {completed.returncode}"


def run_generate_command(
    db_path: Path,
    run_date: str,
    scheduled_time: str,
    actual_time: str,
) -> tuple[bool, str]:
    log(f"开始生成 {run_date} 日报，计划时间={scheduled_time}。")
    completed = subprocess.run(
        [sys.executable, "-m", "src.main", "--dry-run"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
        check=False,
    )
    summary = _command_summary(completed)
    report = get_report_by_date(run_date, db_path)
    if completed.returncode == 0 and report:
        record_scheduler_run(
            run_date,
            scheduled_time,
            "success",
            summary or "今日日报生成成功。",
            actual_time,
            db_path,
            task_type="generate",
        )
        log(f"{run_date} 日报生成成功。")
        return True, summary

    if completed.returncode == 0:
        summary = "生成命令结束，但数据库中没有找到今日日报。"
    record_scheduler_run(
        run_date,
        scheduled_time,
        "failed",
        summary,
        actual_time,
        db_path,
        task_type="generate",
    )
    log(f"{run_date} 日报生成失败：{summary[-300:]}")
    return False, summary


def ensure_today_report(
    db_path: Path,
    run_date: str,
    scheduled_time: str,
    actual_time: str,
    allow_retry_for_new_slot: bool = False,
) -> dict[str, object]:
    report = get_report_by_date(run_date, db_path)
    if report:
        return {
            "generated_today": True,
            "generation_status": "exists",
            "generation_message": "今天日报已经存在，跳过生成。",
            "report_id": int(report["id"]),
        }

    latest = _latest_task_run(db_path, "generate")
    if (
        latest
        and str(latest.get("run_date")) == run_date
        and str(latest.get("status")) == "failed"
        and not (
            allow_retry_for_new_slot
            and str(latest.get("scheduled_time")) != scheduled_time
        )
    ):
        return {
            "generated_today": False,
            "generation_status": "failed",
            "generation_message": (
                "今天自动生成已经失败过，已停止自动重试；"
                "请在网页点击“立即生成今日日报”。"
            ),
        }

    ok, summary = run_generate_command(
        db_path,
        run_date,
        scheduled_time,
        actual_time,
    )
    report = get_report_by_date(run_date, db_path)
    return {
        "generated_today": bool(ok and report),
        "generation_status": "success" if ok and report else "failed",
        "generation_message": (
            "今日日报生成成功。"
            if ok and report
            else f"今日日报生成失败：{summary[-300:]}"
        ),
        "report_id": int(report["id"]) if report else 0,
    }


def deliver_today_report(
    db_path: Path,
    run_date: str,
    scheduled_time: str,
    actual_time: str,
) -> tuple[bool, str]:
    try:
        result = deliver_stored_report(
            report_date=run_date,
            delivery_type="scheduled",
            db_path=db_path,
        )
        message = str(result.get("message") or "今日日报邮件发送成功。")
        record_scheduler_run(
            run_date,
            scheduled_time,
            "success",
            message,
            actual_time,
            db_path,
            task_type="email",
        )
        log(f"{run_date} 邮件发送成功。")
        return True, message
    except (LookupError, ReportDeliveryError, RuntimeError) as exc:
        message = str(exc).strip() or f"邮件发送失败：{type(exc).__name__}"
        record_scheduler_run(
            run_date,
            scheduled_time,
            "failed",
            message,
            actual_time,
            db_path,
            task_type="email",
        )
        log(f"{run_date} 邮件发送失败：{message[-300:]}")
        return False, message


def check_once(db_path: Path) -> dict[str, object]:
    values = get_email_settings(db_path)
    email_enabled = bool(values["email_enabled"])
    auto_send_enabled = bool(values["auto_send_local_enabled"])
    scheduled_time = str(values["email_send_time"])
    grace_minutes = int(values.get("send_grace_minutes") or 180)
    timezone_name = str(values["timezone"])

    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return _base_result(
            "failed",
            f"时区无效：{timezone_name}",
            email_enabled=email_enabled,
            auto_send_local_enabled=auto_send_enabled,
            generation_time=GENERATION_TIME,
            scheduled_time=scheduled_time,
            send_grace_minutes=grace_minutes,
        )

    now = datetime.now(zone)
    run_date = now.date().isoformat()
    actual_time = now.strftime("%H:%M")
    generation_at = _time_at(now, GENERATION_TIME)
    common = {
        "email_enabled": email_enabled,
        "auto_send_local_enabled": auto_send_enabled,
        "timezone": timezone_name,
        "run_date": run_date,
        "current_time": actual_time,
        "generation_time": GENERATION_TIME,
        "scheduled_time": scheduled_time,
        "send_grace_minutes": grace_minutes,
    }

    report = get_report_by_date(run_date, db_path)
    generation_result = {
        "generated_today": bool(report),
        "generation_status": "exists" if report else "pending",
        "generation_message": (
            "今天日报已经存在。"
            if report
            else "今天还没有生成日报，可手动生成。"
        ),
        "report_id": int(report["id"]) if report else 0,
    }
    if not report and now >= generation_at:
        generation_result = ensure_today_report(
            db_path,
            run_date,
            GENERATION_TIME,
            actual_time,
        )

    if generation_result["generation_status"] == "failed":
        return _base_result(
            "failed",
            str(generation_result["generation_message"]),
            email_status="not_started",
            email_message="生成失败，邮件发送未执行。",
            already_sent=False,
            **generation_result,
            **common,
        )

    if not email_enabled:
        return _base_result(
            "skipped",
            "邮件发送已关闭；本地调度器只负责生成日报。",
            email_status="disabled",
            email_message="邮件发送已关闭。",
            already_sent=False,
            **generation_result,
            **common,
        )

    if not auto_send_enabled:
        return _base_result(
            "skipped",
            "本地自动发送已关闭；今日日报会生成，但不会自动发邮件。",
            email_status="disabled",
            email_message="本地自动发送已关闭。",
            already_sent=False,
            **generation_result,
            **common,
        )

    try:
        send_at = _time_at(now, scheduled_time)
    except ValueError as exc:
        return _base_result(
            "failed",
            str(exc),
            email_status="failed",
            email_message=str(exc),
            already_sent=False,
            **generation_result,
            **common,
        )

    grace_until = send_at + timedelta(minutes=grace_minutes)
    common["grace_until"] = grace_until.strftime("%H:%M")

    latest_email = _latest_task_run(db_path, "email")
    if (
        latest_email
        and str(latest_email.get("run_date")) == run_date
        and str(latest_email.get("scheduled_time")) == scheduled_time
        and str(latest_email.get("status")) == "failed"
    ):
        message = "今天自动邮件已经失败过，已停止自动重试；可在网页点击“立即发送今天日报”。"
        return _base_result(
            "failed",
            message,
            email_status="failed",
            email_message=message,
            already_sent=False,
            **generation_result,
            **common,
        )

    report = get_report_by_date(run_date, db_path)
    sent_by_report = bool(report and report.get("email_sent"))
    sent_by_scheduler = scheduler_has_success(
        run_date,
        scheduled_time=scheduled_time,
        task_type="email",
        db_path=db_path,
    )
    if sent_by_report or sent_by_scheduler:
        message = f"{run_date} 今天已经成功发送过邮件，跳过重复自动发送。"
        return _base_result(
            "skipped",
            message,
            email_status="sent",
            email_message=message,
            already_sent=True,
            **generation_result,
            **common,
        )

    if now < send_at:
        seconds = int((send_at - now).total_seconds())
        minutes_left = max(1, (seconds + 59) // 60)
        message = (
            f"当前时间 {actual_time}，计划发送 {scheduled_time}，"
            f"距离发送还有 {_minutes_text(minutes_left)}。"
        )
        return _base_result(
            "pending",
            message,
            email_status="pending",
            email_message=message,
            already_sent=False,
            minutes_until_send=minutes_left,
            **generation_result,
            **common,
        )

    if now > grace_until:
        message = (
            f"今天已经超过计划发送时间 {scheduled_time} 后 "
            f"{grace_minutes} 分钟宽限窗口，跳过自动发送。"
        )
        if not latest_email or str(latest_email.get("run_date")) != run_date:
            record_scheduler_run(
                run_date,
                scheduled_time,
                "skipped",
                message,
                actual_time,
                db_path,
                task_type="email",
            )
        return _base_result(
            "skipped",
            message,
            email_status="skipped",
            email_message=message,
            already_sent=False,
            **generation_result,
            **common,
        )

    report = get_report_by_date(run_date, db_path)
    if not report:
        generation_result = ensure_today_report(
            db_path,
            run_date,
            scheduled_time,
            actual_time,
            allow_retry_for_new_slot=True,
        )
        if generation_result["generation_status"] == "failed":
            message = "发送前生成今日日报失败，邮件未发送。"
            record_scheduler_run(
                run_date,
                scheduled_time,
                "failed",
                str(generation_result["generation_message"]),
                actual_time,
                db_path,
                task_type="email",
            )
            return _base_result(
                "failed",
                message,
                email_status="failed",
                email_message=str(generation_result["generation_message"]),
                already_sent=False,
                **generation_result,
                **common,
            )

    message = (
        f"当前时间 {actual_time} 已到达计划发送 {scheduled_time}，"
        f"且仍在 {grace_minutes} 分钟宽限窗口内，准备发送已生成日报。"
    )
    log(message)
    sent, send_message = deliver_today_report(
        db_path,
        run_date,
        scheduled_time,
        actual_time,
    )
    return _base_result(
        "success" if sent else "failed",
        f"{message} 结果：{'成功' if sent else '失败'}。",
        email_status="success" if sent else "failed",
        email_message=send_message,
        already_sent=sent,
        **generation_result,
        **common,
    )


def format_result(result: dict[str, object]) -> str:
    lines = [
        f"当前时间：{result.get('current_time', '未知')} {result.get('timezone', '')}",
        f"日报生成时间：{result.get('generation_time', GENERATION_TIME)}",
        f"今天日报已生成：{'是' if result.get('generated_today') else '否'}",
        f"生成状态：{result.get('generation_status', 'unknown')}",
        f"生成结果：{result.get('generation_message', '')}",
        f"邮件发送：{'启用' if result.get('email_enabled') else '未启用'}",
        (
            "本地自动发送："
            f"{'启用' if result.get('auto_send_local_enabled') else '未启用'}"
        ),
        f"邮件计划时间：{result.get('scheduled_time', '未知')}",
        f"补发宽限：{result.get('send_grace_minutes', 180)} 分钟",
        f"当天已成功发邮件：{'是' if result.get('already_sent') else '否'}",
        f"邮件状态：{result.get('email_status', 'unknown')}",
        f"邮件结果：{result.get('email_message', '')}",
        f"总体状态：{result.get('status')}",
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
        write_scheduler_status(
            "running",
            "本地调度器已启动：07:30 生成日报，邮件按设置可选发送。",
        )
        log(f"本地调度器启动，检查间隔 {interval} 秒。")
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
        log("本地调度器收到停止请求。")
        return 0
    except Exception as exc:
        message = f"调度器异常：{type(exc).__name__}: {exc}"
        write_scheduler_status("failed", message)
        log(message)
        return 1


if __name__ == "__main__":
    arguments = parse_args()
    raise SystemExit(run_scheduler(arguments.interval, arguments.once))
