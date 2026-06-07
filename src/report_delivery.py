from pathlib import Path
from typing import Dict, Optional

from src.config import load_settings
from src.database import (
    DEFAULT_DB_PATH,
    get_email_settings,
    get_report,
    get_report_by_date,
    record_email_delivery,
)
from src.sender import send_email


class ReportDeliveryError(RuntimeError):
    def __init__(self, message: str, result: Dict[str, object]):
        super().__init__(message)
        self.result = result


def deliver_stored_report(
    *,
    report_id: Optional[int] = None,
    report_date: str = "",
    delivery_type: str = "manual",
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    """发送 SQLite 中已有日报，不触发抓取、评分或生成流程。"""

    if (report_id is None) == (not report_date.strip()):
        raise ValueError("必须且只能提供 report_id 或 report_date。")

    report = (
        get_report(int(report_id), db_path)
        if report_id is not None
        else get_report_by_date(report_date, db_path)
    )
    if not report:
        target = (
            f"report_id={report_id}"
            if report_id is not None
            else f"report_date={report_date}"
        )
        raise LookupError(f"找不到历史日报：{target}。")

    current_report_id = int(report["id"])
    current_report_date = str(report["report_date"])
    try:
        email_settings = get_email_settings(db_path)
        if not bool(email_settings["email_enabled"]):
            raise RuntimeError("邮件推送已关闭，请先在设置页开启。")

        settings = load_settings(send_email=True, require_api_key=False)
        send_email(
            settings,
            str(report.get("markdown_content") or ""),
            str(report.get("html_content") or ""),
            current_report_date,
            dry_run=False,
        )
        message = "历史日报邮件发送成功。"
        delivery_id = record_email_delivery(
            current_report_id,
            current_report_date,
            "success",
            message,
            delivery_type=delivery_type,
            db_path=db_path,
        )
        return {
            "delivery_id": delivery_id,
            "report_id": current_report_id,
            "report_date": current_report_date,
            "delivery_type": delivery_type,
            "status": "success",
            "message": message,
        }
    except Exception as exc:
        if isinstance(exc, ReportDeliveryError):
            raise
        message = str(exc).strip() or f"邮件发送失败（{type(exc).__name__}）。"
        delivery_id = record_email_delivery(
            current_report_id,
            current_report_date,
            "failed",
            message,
            delivery_type=delivery_type,
            db_path=db_path,
        )
        result = {
            "delivery_id": delivery_id,
            "report_id": current_report_id,
            "report_date": current_report_date,
            "delivery_type": delivery_type,
            "status": "failed",
            "message": message,
        }
        raise ReportDeliveryError(message, result) from exc
