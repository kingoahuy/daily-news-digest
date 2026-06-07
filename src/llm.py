import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from openai import OpenAI

from src.config import Settings
from src.models import NewsItem
from src.ranker import extract_keywords


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "daily_report_prompt.txt"
CATEGORY_NAMES = {
    "technology": "三、科技动态 / Technology",
    "finance": "四、财经动态 / Finance",
    "sports": "五、体育运动 / Sports",
    "society": "六、社会大事 / Society",
    "politics": "七、政治事件 / Politics",
}
CATEGORY_ORDER = ["technology", "finance", "sports", "society", "politics"]


def news_item_to_dict(item: NewsItem) -> Dict[str, object]:
    """把 NewsItem 转成只包含 RSS 和本项目处理结果的 JSON。"""

    return {
        "title": item.title,
        "summary": item.summary,
        "url": item.url,
        "source": item.source,
        "category": item.category,
        "subcategory": item.subcategory,
        "keywords": sorted(extract_keywords(item)),
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "rule_score": item.rule_score,
        "ai_score": item.ai_score,
        "ai_reason": item.ai_reason,
        "ai_summary": item.ai_summary,
        "ai_tags": item.ai_tags,
        "importance_tier": item.importance_tier,
        "final_score": item.score,
        "preference_adjustment": item.preference_adjustment,
        "cluster_id": item.cluster_id,
        "cluster_title": item.cluster_title,
        "enrichment": item.enrichment,
    }


def _date_text(report_date: Union[date, datetime, str]) -> str:
    if isinstance(report_date, (date, datetime)):
        return report_date.strftime("%Y-%m-%d")
    return str(report_date)


def _fact_text(item: NewsItem) -> str:
    return item.ai_summary or item.summary or item.title


def _source_line(item: NewsItem) -> str:
    return f"[{item.source}]({item.url})"


def _enrichment_lines(item: NewsItem) -> List[str]:
    enrichment = item.enrichment or {}
    if not enrichment:
        return []
    labels = (
        ("whats_new", "最新变化 / What's new"),
        ("why_it_matters", "为何重要 / Why it matters"),
        ("background", "背景 / Background"),
        ("possible_impact", "可能影响 / Possible impact"),
    )
    lines = []
    for key, label in labels:
        value = str(enrichment.get(key, "")).strip()
        if value:
            lines.extend([f"**{label}**", value, ""])
    points = enrichment.get("follow_up_points") or []
    if points:
        lines.append("**后续看点 / Follow-up points**")
        lines.extend(f"- {point}" for point in points)
        lines.append("")
    return lines


def _category_block(category: str, items: List[NewsItem]) -> List[str]:
    lines = [f"## {CATEGORY_NAMES[category]}", ""]
    if not items:
        return lines + [
            "### 中文",
            "今日该分类没有达到评分阈值的有效新闻。",
            "",
            "### English",
            "No valid items in this category met today's score threshold.",
            "",
        ]

    for item in items:
        tags = " / ".join(item.ai_tags or sorted(extract_keywords(item))) or "未识别"
        lines.extend(
            [
                f"### {item.title}",
                f"- **AI 分数 / AI score**：{item.ai_score:.2f}/10 "
                f"({item.importance_tier})",
                f"- **摘要 / Summary**：{_fact_text(item)}",
                f"- **推荐理由 / Why selected**：{item.ai_reason}",
                f"- **标签 / Tags**：{tags}",
                f"- **主题簇 / Story cluster**：{item.cluster_title or item.title}",
                f"- **来源 / Source**：{_source_line(item)}",
                "",
            ]
        )
    return lines


def build_fallback_report(
    core_topic: NewsItem,
    grouped_news: Dict[str, List[NewsItem]],
    report_date: Union[date, datetime, str],
    radar_stats: Optional[Dict[str, object]] = None,
) -> str:
    """DeepSeek 不可用时仍输出完整的中英文双语新闻雷达。"""

    date_text = _date_text(report_date)
    stats = radar_stats or {}
    selected_count = sum(len(items) for items in grouped_news.values())
    filtered_count = int(stats.get("filtered_count", 0))
    lines = [
        f"# 个人 AI 新闻雷达 / Personal AI News Radar｜{date_text}",
        "",
        (
            f"> 中文：本期选择 {selected_count} 条主题代表新闻，"
            f"过滤 {filtered_count} 条低分新闻。"
        ),
        (
            f"> English: This edition selected {selected_count} representative "
            f"stories and filtered {filtered_count} low-scoring items."
        ),
        "",
        "## 一、今日重点 / Today's Highlights",
        "",
        "### 中文",
        f"本期最高优先级新闻是“{core_topic.title}”。"
        "排序综合了规则分、AI 重要性分、跨来源主题聚类和个人偏好。",
        "当前简报只使用 RSS 标题、摘要和链接，没有读取新闻全文。",
        "",
        "### English",
        f'The highest-priority story is "{core_topic.title}". '
        "Ranking combines rule-based signals, AI importance, cross-source "
        "story clustering, and personal preferences.",
        "This digest uses only RSS titles, summaries, and links; it does not "
        "read full articles.",
        "",
        "## 二、核心新闻 / Core Stories",
        "",
        f"### {core_topic.title}",
        f"- **AI 分数 / AI score**：{core_topic.ai_score:.2f}/10 "
        f"({core_topic.importance_tier})",
        f"- **摘要 / Summary**：{_fact_text(core_topic)}",
        f"- **推荐理由 / Why selected**：{core_topic.ai_reason}",
        f"- **来源 / Source**：{_source_line(core_topic)}",
        "",
    ]
    lines.extend(_enrichment_lines(core_topic))

    for category in CATEGORY_ORDER:
        lines.extend(_category_block(category, grouped_news.get(category, [])))

    lines.extend(
        [
            "## 八、今日观察 / Daily Observations",
            "",
            "### 中文",
            "多来源主题会获得额外关注，但多来源出现本身不等于事实已完全确认。"
            "摘要信息有限的条目只保留可追溯事实。",
            "",
            "### English",
            "Stories covered by multiple sources receive additional attention, "
            "but repeated coverage alone does not fully verify a claim. Items "
            "with limited summaries retain only traceable facts.",
            "",
            "## 九、我的关注建议 / Personal Follow-up",
            "",
        ]
    )
    for label_zh, label_en, category in (
        ("科技", "Technology", "technology"),
        ("财经", "Finance", "finance"),
        ("体育", "Sports", "sports"),
    ):
        items = grouped_news.get(category, [])
        if items:
            item = items[0]
            lines.append(
                f"- **{label_zh} / {label_en}**："
                f"[{item.title}]({item.url})"
            )
        else:
            lines.append(
                f"- **{label_zh} / {label_en}**："
                "今日无高分条目 / No high-scoring item today."
            )

    return "\n".join(lines).strip() + "\n"


def generate_daily_report(
    settings: Settings,
    core_topic: NewsItem,
    grouped_news: Dict[str, List[NewsItem]],
    top_news: List[NewsItem],
    report_date: Union[date, datetime, str],
    preference_profile: Optional[Dict[str, object]] = None,
    clusters: Optional[List[Dict[str, object]]] = None,
    radar_stats: Optional[Dict[str, object]] = None,
) -> str:
    """调用 DeepSeek 生成双语简报；异常时退回双语本地模板。"""

    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        profile = preference_profile or {}
        payload = {
            "report_date": _date_text(report_date),
            "core_topic": news_item_to_dict(core_topic),
            "grouped_news": {
                category: [news_item_to_dict(item) for item in items]
                for category, items in grouped_news.items()
            },
            "top_news": [news_item_to_dict(item) for item in top_news],
            "story_clusters": clusters or [],
            "radar_stats": radar_stats or {},
            "user_preferences": {
                "user_profile": profile.get("user_profile", {}),
                "category_weights": profile.get("category_weights", {}),
                "subcategory_weights": profile.get("subcategory_weights", {}),
                "feedback_count": profile.get("feedback_count", 0),
                "category_averages": profile.get("category_averages", {}),
                "keyword_averages": profile.get("keyword_averages", {}),
                "interaction_count": profile.get("interaction_count", 0),
                "interaction_category_adjustments": profile.get(
                    "interaction_category_adjustments", {}
                ),
                "interaction_keyword_adjustments": profile.get(
                    "interaction_keyword_adjustments", {}
                ),
                "interaction_source_adjustments": profile.get(
                    "interaction_source_adjustments", {}
                ),
            },
        }

        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=120.0,
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        "请根据以下数据生成中英文双语 AI 新闻雷达：\n"
                        + json.dumps(payload, ensure_ascii=False, indent=2)
                    ),
                },
            ],
            temperature=0.2,
            stream=False,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("DeepSeek 返回了空内容。")
        return content.strip() + "\n"
    except Exception as exc:
        print(
            "警告：DeepSeek 日报生成失败"
            f"（{type(exc).__name__}），将生成本地双语 fallback 简报。"
        )
        return build_fallback_report(
            core_topic,
            grouped_news,
            report_date,
            radar_stats=radar_stats,
        )
