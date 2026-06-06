import argparse
from datetime import datetime
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from src.config import ConfigError, load_settings
from src.fetcher import fetch_news
from src.formatter import format_and_save_report
from src.llm import generate_daily_report
from src.ranker import rank_news
from src.sender import send_email


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成并发送每日热点新闻日报。")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只生成日报，不发邮件")
    mode.add_argument("--send", action="store_true", help="生成日报并发送邮件")
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    send_mode = bool(args.send)
    mode_name = "send" if send_mode else "dry-run"
    print(f"当前运行模式：{mode_name}")

    try:
        settings = load_settings(send_email=send_mode)
        report_date = datetime.now(ZoneInfo(settings.timezone)).date()

        items = fetch_news(settings)
        print(f"本次抓取并去重后共有 {len(items)} 条新闻。")

        ranked = rank_news(items, settings)
        core_topic = ranked["core_topic"]
        grouped_news = ranked["grouped_news"]
        top_news = ranked["top_news"]
        print(f"选择的核心议题：{core_topic.title}")

        markdown_text = generate_daily_report(
            settings,
            core_topic,
            grouped_news,
            top_news,
            report_date,
        )
        markdown_text, html_text, report_path = format_and_save_report(
            markdown_text, report_date
        )
        print(f"日报保存路径：{report_path.resolve()}")

        sent = send_email(
            settings,
            markdown_text,
            html_text,
            report_date,
            dry_run=not send_mode,
        )
        print(f"是否发送成功：{'是' if sent else '否（dry-run）'}")
        return 0
    except (ConfigError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}")
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
