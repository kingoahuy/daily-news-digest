import argparse
from datetime import datetime
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from src.ai_scorer import apply_rule_only_score, score_news_with_ai
from src.config import load_settings
from src.database import (
    get_generation_settings,
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


def _print_task_failure(stage: str, exc: Exception) -> None:
    print("=" * 60)
    print("日报生成任务失败")
    print(f"失败阶段：{stage}")
    print(f"错误类型：{type(exc).__name__}")
    print(f"错误信息：{exc}")
    print("排查建议：")
    print("1. 检查 GitHub Secrets 是否完整，或先运行环境预检脚本")
    print("2. 检查 DeepSeek API Key、模型名称和接口地址是否有效")
    print("3. 检查 SMTP 主机、端口、账号和授权码是否正确")
    print("4. 检查 RSS、数据库和 GitHub Pages 目录是否可访问")
    print("安全提示：日志不会主动打印 API Key 或 SMTP_PASSWORD。")
    print("=" * 60)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成并发送 AI 新闻雷达。")
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
    current_stage = "启动"

    try:
        current_stage = "加载配置和检查数据库"
        print("步骤 1/12：加载 V5 配置并检查数据库。")
        settings = load_settings(send_email=send_mode)
        initialize_database(settings.database_path)
        generation_settings = get_generation_settings(
            settings.filtering,
            settings.database_path,
        )
        settings.filtering.update(generation_settings)
        settings.filtering["ai_scoring_mode"] = (
            "top_candidates_only"
            if bool(generation_settings["low_api_mode"])
            else "all_items"
        )
        report_date = datetime.now(ZoneInfo(settings.timezone)).date()
        print(
            "生成设置："
            f"省 API={'开启' if generation_settings['low_api_mode'] else '关闭'}，"
            f"日报最多 {generation_settings['max_total_news']} 条，"
            f"AI 候选 {generation_settings['pre_ai_prefilter_limit']} 条。"
        )

        current_stage = "抓取 RSS 新闻"
        print("步骤 2/12：抓取 RSS 新闻。")
        fetched_items = fetch_news(settings, settings.feeds_path)
        fetched_count = len(fetched_items)
        print(f"RSS 新闻抓取成功：{fetched_count} 条。")

        current_stage = "新闻初步去重"
        print("步骤 3/12：执行 URL 和标题初步去重。")
        if bool(settings.filtering.get("enable_deduplication", True)):
            items = deduplicate_news(fetched_items)
        else:
            items = fetched_items
        print(
            f"初步去重完成：保留 {len(items)} 条，"
            f"移除 {fetched_count - len(items)} 条。"
        )

        current_stage = "本地规则评分"
        print("步骤 4/12：计算本地规则分。")
        keyword_map = score_news_by_rules(items, settings)

        current_stage = "DeepSeek 重要性评分"
        print("步骤 5/12：筛选候选并执行 DeepSeek 重要性评分。")
        scoring_mode = str(
            settings.filtering.get(
                "ai_scoring_mode",
                "top_candidates_only",
            )
        )
        candidate_limit = max(
            1,
            int(settings.filtering.get("pre_ai_prefilter_limit", 40)),
        )
        if scoring_mode == "top_candidates_only":
            ai_candidates = sorted(
                items,
                key=lambda item: item.rule_score,
                reverse=True,
            )[:candidate_limit]
        else:
            ai_candidates = list(items)
        candidate_ids = {id(item) for item in ai_candidates}
        for item in items:
            if id(item) not in candidate_ids:
                apply_rule_only_score(item)
        print(
            f"AI 精评候选：{len(ai_candidates)} 条；"
            f"本地规则评分：{len(items) - len(ai_candidates)} 条。"
        )
        scoring_stats = score_news_with_ai(ai_candidates, settings)
        scoring_stats["rule_only"] = len(items) - len(ai_candidates)
        scoring_stats["candidate_limit"] = candidate_limit
        scoring_stats["mode"] = scoring_mode

        current_stage = "新闻主题聚类"
        print("步骤 6/12：执行主题聚类。")
        clusters = cluster_news(items)
        duplicate_story_count = sum(
            len(cluster.related_items) for cluster in clusters
        )
        print(
            f"主题聚类完成：{len(clusters)} 个主题簇，"
            f"合并 {duplicate_story_count} 条同事件新闻。"
        )

        current_stage = "偏好学习和最终排序"
        print("步骤 7/12：读取互动偏好并计算最终分数。")
        ranked = rank_news(
            items,
            settings,
            clusters=clusters,
            keyword_map=keyword_map,
        )
        core_topic = ranked["core_topic"]
        grouped_news = ranked["grouped_news"]
        top_news = ranked["top_news"]
        preference_profile = ranked["preference_profile"]
        print(
            f"阈值过滤完成：通过 {ranked['eligible_count']} 条，"
            f"过滤 {ranked['filtered_count']} 条低分主题。"
        )
        print(
            f"最终精选 {ranked['selected_count']} 条，"
            f"Top 新闻 {len(top_news)} 条。"
        )
        print(f"选择的核心议题：{core_topic.title}")

        current_stage = "核心新闻背景补充"
        print("步骤 8/12：补充核心新闻背景。")
        enrichment_stats = enrich_core_news(
            top_news,
            settings,
            clusters=clusters,
        )

        selected_news = _selected_news(grouped_news)
        selected_cluster_ids = {
            item.cluster_id for item in selected_news if item.cluster_id
        }
        selected_cluster_rows = [
            cluster_to_dict(cluster)
            for cluster in clusters
            if cluster.cluster_id in selected_cluster_ids
        ]
        all_cluster_rows = [cluster_to_dict(cluster) for cluster in clusters]
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
            "clusters": all_cluster_rows,
        }

        bilingual = bool(
            settings.filtering.get("enable_bilingual_report", False)
        )
        current_stage = "生成双语日报"
        print(
            "步骤 9/12：生成"
            f"{'中英文双语' if bilingual else '中文精简版'}日报。"
        )
        markdown_text = generate_daily_report(
            settings,
            core_topic,
            grouped_news,
            top_news,
            report_date,
            preference_profile=preference_profile,
            clusters=selected_cluster_rows,
            radar_stats=radar_stats,
        )
        markdown_text, html_text, report_path = format_and_save_report(
            markdown_text,
            report_date,
        )
        print(f"日报保存路径：{report_path.resolve()}")

        current_stage = "保存日报和 AI 雷达数据"
        print("步骤 10/12：保存日报和 AI 雷达数据到 SQLite。")
        report_id = None
        try:
            report_id = save_report(
                report_date=report_date.isoformat(),
                title=(
                    (
                        "个人 AI 新闻雷达 / Personal AI News Radar"
                        if bilingual
                        else "每日热点新闻简报"
                    )
                    + f"｜{report_date.isoformat()}"
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

        current_stage = "GitHub Pages 导出"
        print("步骤 11/12：检查 GitHub Pages 导出。")
        page_config = dict(settings.delivery.get("github_pages") or {})
        export_enabled = bool(page_config.get("enabled", False))
        pages_error = None
        if args.export_pages or export_enabled:
            try:
                export_result = export_pages_from_settings(settings)
                print(
                    f"GitHub Pages 导出完成："
                    f"{export_result['copied_count']} 篇日报，"
                    f"索引={export_result['index_path']}"
                )
            except Exception as exc:
                pages_error = RuntimeError(
                    "GitHub Pages 导出失败"
                    f"（{type(exc).__name__}）：{exc}"
                )
                print(
                    "警告：GitHub Pages 导出失败，将继续尝试邮件投递；"
                    "任务最终仍会返回失败以便排查。"
                )
        else:
            print("GitHub Pages 导出未启用，可使用 --export-pages。")

        current_stage = "邮件投递"
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
        if pages_error is not None:
            current_stage = "GitHub Pages 导出"
            raise pages_error

        print(f"是否发送成功：{'是' if sent else '否（dry-run）'}")
        return 0
    except Exception as exc:
        _print_task_failure(current_stage, exc)
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
