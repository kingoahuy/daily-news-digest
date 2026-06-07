import argparse
from datetime import datetime
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from src.ai_scorer import score_news_with_ai
from src.config import ConfigError, load_settings
from src.database import (
    initialize_database,
    save_news_items,
    save_report,
    update_report_email_status,
)
from src.deduplicator import (
    cluster_news,
    cluster_to_dict,
    deduplicate_news,
)
from src.enricher import enrich_core_news
from src.fetcher import fetch_news
from src.formatter import format_and_save_report
from src.llm import generate_daily_report
from src.pages_exporter import export_pages_from_settings
from src.ranker import rank_news, score_news_by_rules
from src.sender import send_email


def _selected_news(grouped_news):
    """按分类顺序去重，得到真正进入日报和数据库的主题代表新闻。"""

    selected = []
    seen = set()
    for items in grouped_news.values():
        for item in items:
            key = item.cluster_id or (item.url, item.title)
            if key in seen:
                continue
            seen.add(key)
            selected.append(item)
    return selected


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成并发送双语 AI 新闻雷达。")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只生成日报，不发邮件")
    mode.add_argument("--send", action="store_true", help="生成日报并发送邮件")
    parser.add_argument(
        "--export-pages",
        action="store_true",
        help="同时更新 docs/ 下的 GitHub Pages 静态归档",
    )
    return parser.parse_args(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    send_mode = bool(args.send)
    mode_name = "send" if send_mode else "dry-run"
    print(f"当前运行模式：{mode_name}")

    try:
        print("步骤 1/12：加载 V4 配置并检查数据库。")
        settings = load_settings(send_email=send_mode)
        initialize_database(settings.database_path)
        report_date = datetime.now(ZoneInfo(settings.timezone)).date()

        print("步骤 2/12：抓取 RSS 新闻。")
        fetched_items = fetch_news(settings, settings.feeds_path)
        fetched_count = len(fetched_items)
        print(f"RSS 新闻抓取成功：{fetched_count} 条。")

        print("步骤 3/12：执行 URL 和标题初步去重。")
        if bool(settings.filtering.get("enable_deduplication", True)):
            items = deduplicate_news(fetched_items)
        else:
            items = fetched_items
        print(
            f"初步去重完成：保留 {len(items)} 条，"
            f"移除 {fetched_count - len(items)} 条。"
        )

        print("步骤 4/12：计算本地规则分。")
        keyword_map = score_news_by_rules(items, settings)

        print("步骤 5/12：批量执行 DeepSeek 重要性评分。")
        scoring_stats = score_news_with_ai(items, settings)

        print("步骤 6/12：执行主题聚类。")
        clusters = cluster_news(items)
        duplicate_story_count = sum(
            len(cluster.related_items) for cluster in clusters
        )
        print(
            f"主题聚类完成：{len(clusters)} 个主题簇，"
            f"合并 {duplicate_story_count} 条同事件新闻。"
        )

        print("步骤 7/12：读取互动偏好并计算最终分数。")
        ranked = rank_news(items, settings, clusters=clusters)
        core_topic = ranked["core_topic"]
        grouped_news = ranked["grouped_news"]
        top_news = ranked["top_news"]
        preference_profile = ranked["preference_profile"]
        print(
            f"阈值过滤完成：通过 {ranked['eligible_count']} 条，"
            f"过滤 {ranked['filtered_count']} 条低分主题。"
        )
        print(f"选择的核心议题：{core_topic.title}")

        print("步骤 8/12：补充核心新闻双语背景。")
        enrichment_stats = enrich_core_news(
            top_news,
            settings,
            clusters=clusters,
        )

        selected_news = _selected_news(grouped_news)
        selected_cluster_ids = {
            item.cluster_id for item in selected_news if item.cluster_id
        }
        cluster_rows = [
            cluster_to_dict(cluster)
            for cluster in clusters
            if cluster.cluster_id in selected_cluster_ids
        ]
        radar_stats = {
            "fetched_count": fetched_count,
            "deduplicated_count": len(items),
            "exact_duplicate_count": fetched_count - len(items),
            "cluster_count": len(clusters),
            "clustered_duplicate_count": duplicate_story_count,
            "multi_source_cluster_count": sum(
                1 for cluster in clusters if len(cluster.sources) > 1
            ),
            "eligible_count": ranked["eligible_count"],
            "filtered_count": ranked["filtered_count"],
            "selected_count": len(selected_news),
            "category_averages": ranked["category_averages"],
            "preference_impact": ranked["preference_impact"],
            "ai_scoring": scoring_stats,
            "enrichment": enrichment_stats,
            "clusters": cluster_rows,
        }

        print("步骤 9/12：生成中英文双语日报。")
        markdown_text = generate_daily_report(
            settings,
            core_topic,
            grouped_news,
            top_news,
            report_date,
            preference_profile=preference_profile,
            clusters=cluster_rows,
            radar_stats=radar_stats,
        )
        markdown_text, html_text, report_path = format_and_save_report(
            markdown_text,
            report_date,
        )
        print(f"双语日报保存路径：{report_path.resolve()}")

        print("步骤 10/12：保存日报和 AI 雷达数据到 SQLite。")
        report_id = None
        try:
            report_id = save_report(
                report_date=report_date.isoformat(),
                title=(
                    f"个人 AI 新闻雷达 / Personal AI News Radar｜"
                    f"{report_date.isoformat()}"
                ),
                core_topic=core_topic.title,
                markdown_content=markdown_text,
                html_content=html_text,
                email_sent=False,
                report_path=str(report_path.resolve()),
                radar_stats=radar_stats,
                db_path=settings.database_path,
            )
            saved_count = save_news_items(
                report_id,
                selected_news,
                keyword_map=keyword_map,
                db_path=settings.database_path,
            )
            print(
                f"数据库保存成功：report_id={report_id}，"
                f"主题代表新闻={saved_count}，"
                f"路径={settings.database_path.resolve()}"
            )
        except Exception as exc:
            print(
                f"警告：数据库写入失败（{type(exc).__name__}），"
                "将继续处理 Pages 和邮件。"
            )

        print("步骤 11/12：检查 GitHub Pages 导出。")
        page_config = dict(settings.delivery.get("github_pages") or {})
        export_enabled = bool(page_config.get("enabled", False))
        if args.export_pages or export_enabled:
            export_result = export_pages_from_settings(settings)
            print(
                f"GitHub Pages 导出完成："
                f"{export_result['copied_count']} 篇日报，"
                f"索引={export_result['index_path']}"
            )
        else:
            print("GitHub Pages 导出未启用，可使用 --export-pages。")

        print("步骤 12/12：处理邮件投递。")
        sent = False
        email_error = None
        try:
            sent = send_email(
                settings,
                markdown_text,
                html_text,
                report_date,
                dry_run=not send_mode,
            )
        except RuntimeError as exc:
            email_error = exc

        if report_id is not None:
            try:
                update_report_email_status(
                    report_id,
                    sent,
                    db_path=settings.database_path,
                )
                print(f"数据库邮件状态已更新：email_sent={int(sent)}")
            except Exception as exc:
                print(
                    f"警告：邮件状态写回失败（{type(exc).__name__}）。"
                )

        if email_error is not None:
            raise email_error

        print(f"是否发送成功：{'是' if sent else '否（dry-run）'}")
        return 0
    except (ConfigError, RuntimeError, ValueError) as exc:
        print(f"错误：{exc}")
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
