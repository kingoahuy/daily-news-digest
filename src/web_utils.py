import json
import subprocess
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List
from zoneinfo import ZoneInfo

from src.config import Settings


RATING_OPTIONS = {
    "很感兴趣": 2,
    "感兴趣": 1,
    "一般": 0,
    "不感兴趣": -1,
    "非常不感兴趣": -2,
}

FEEDBACK_TAGS = [
    "AI",
    "股市",
    "半导体",
    "新能源",
    "斯诺克",
    "网球",
    "乒乓球",
    "NBA",
    "足球",
    "国际政治",
    "社会事件",
    "值得追踪",
    "以后少推",
]

CATEGORY_LABELS = {
    "technology": "科技",
    "finance": "财经",
    "sports": "体育",
    "society": "社会",
    "politics": "政治",
}


def parse_json_list(value: object) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return [part.strip() for part in str(value).split(",") if part.strip()]
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def parse_json_dict(value: object) -> Dict[str, object]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def display_time(value: object) -> str:
    if not value:
        return "未知"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def email_configuration_complete(settings: Settings) -> bool:
    return all(
        [
            settings.smtp_host,
            settings.smtp_user,
            settings.smtp_password,
            settings.mail_from,
            settings.mail_to,
        ]
    )


def run_digest_command(
    project_root: Path,
    send_email: bool = False,
    timeout_seconds: int = 1200,
) -> Dict[str, object]:
    """从网页端调用现有日报主流程。"""

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            "--send" if send_email else "--dry-run",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_send_time(value: object, default: str = "08:13") -> time:
    text = str(value or default)
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return datetime.strptime(default, "%H:%M").time()


def next_email_time_text(
    email_send_time: object,
    timezone_name: str,
    enabled: bool,
) -> str:
    if not enabled:
        return "未启用"
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        return f"{email_send_time}（时区无效）"
    now = datetime.now(zone)
    scheduled = datetime.combine(
        now.date(),
        parse_send_time(email_send_time),
        tzinfo=zone,
    )
    if scheduled <= now:
        scheduled += timedelta(days=1)
    return scheduled.strftime("%m-%d %H:%M")
