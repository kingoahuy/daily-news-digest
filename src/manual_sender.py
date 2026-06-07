import argparse
from datetime import date
from typing import Optional, Sequence

from src.config import ConfigError, load_settings
from src.database import initialize_database
from src.report_delivery import ReportDeliveryError, deliver_stored_report


def _date_argument(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "日期必须使用 YYYY-MM-DD 格式。"
        ) from exc


def _positive_report_id(value: str) -> int:
    report_id = int(value)
    if report_id <= 0:
        raise argparse.ArgumentTypeError("report-id 必须大于 0。")
    return report_id


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="直接发送 SQLite 中已有的历史日报。"
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--date",
        type=_date_argument,
        help="日报日期，格式 YYYY-MM-DD",
    )
    target.add_argument(
        "--report-id",
        type=_positive_report_id,
        help="reports 表中的日报 ID",
    )
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        settings = load_settings(
            send_email=False,
            require_api_key=False,
        )
        initialize_database(settings.database_path)
        result = deliver_stored_report(
            report_id=args.report_id,
            report_date=args.date or "",
            delivery_type="manual",
            db_path=settings.database_path,
        )
        print(
            f"历史日报发送成功：report_id={result['report_id']}，"
            f"date={result['report_date']}，delivery_id={result['delivery_id']}"
        )
        return 0
    except (ConfigError, LookupError, ValueError, ReportDeliveryError) as exc:
        print(f"历史日报发送失败：{exc}")
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
