import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from openai import OpenAI

from src.config import Settings
from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "daily_report_prompt.txt"
CATEGORY_NAMES = {
    "technology": "科技动态",
    "finance": "财经动态",
    "sports": "体育运动",
    "society": "社会动态",
    "politics": "政治动态",
}
CATEGORY_ORDER = ["technology", "finance", "sports", "society", "politics"]


def trim_text(text: object, max_chars: int) -> str:
    """压缩空白并按字符数截断模型输入。"""

    value = " ".join(str(text or "").split())
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return value[: max_chars - 3].rstrip() + "..."


def sanitize_report(markdown: str) -> str:
    """移除容易被误解为交易建议的措辞，并补充财经免责声明。"""

    replacements = {
        "投资者需关注": "后续需关注",
        "投资者应关注": "后续应核验",
        "投资风向标": "行业观察信号",
        "投资机会": "行业变化",
        "建议买入": "建议核验相关信息",
        "建议卖出": "建议核验相关信息",
        "建议配置": "建议持续跟踪",
        "看涨": "预期上行",
        "看跌": "预期下行",
    }
    cleaned = markdown
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    disclaimer = "> 财经内容仅作新闻信息摘要，不构成投资建议。"
    if ("财经" in cleaned or "市场" in cleaned) and disclaimer not in cleaned:
        cleaned = cleaned.rstrip() + "\n\n" + disclaimer + "\n"
    return cleaned


def news_item_to_dict(
    item: NewsItem,
    include_enrichment: bool = False,
) -> Dict[str, object]:
    """只保留日报生成真正需要的可追溯字段。"""

    payload: Dict[str, object] = {
        "title": trim_text(item.title, 180),
        "summary": trim_text(item.summary, 300),
        "source": item.source,
        "category": item.category,
        "url": item.url,
        "ai_score": round(float(item.ai_score or item.rule_score), 2),
        "ai_reason": trim_text(item.ai_reason, 160),
        "ai_tags": [trim_text(tag, 30) for tag in item.ai_tags[:6]],
    }
    if include_enrichment and item.enrichment:
        payload["enrichment"] = item.enrichment
    return payload


def _date_text(report_date: Union[date, datetime, str]) -> str:
    if isinstance(report_date, (date, datetime)):
        return report_date.strftime("%Y-%m-%d")
    return str(report_date)


def _fact_text(item: NewsItem) -> str:
    return trim_text(item.ai_summary or item.summary or item.title, 300)


def _source_line(item: NewsItem) -> str:
    return f"[{item.source}]({item.url})"


def _enrichment_lines(item: NewsItem) -> List[str]:
    enrichment = item.enrichment or {}
    if not enrichment:
        return []
    labels = (
        ("whats_new", "最新变化"),
        ("why_it_matters", "为何重要"),
        ("background", "背景"),
        ("possible_impact", "可能影响"),
    )
    lines: List[str] = []
    for key, label in labels:
        value = trim_text(enrichment.get(key), 360)
        if value:
            lines.append(f"- **{label}**：{value}")
    points = enrichment.get("follow_up_points") or []
    if points:
        lines.append(
            "- **后续看点**："
            + "；".join(trim_text(point, 120) for point in points[:3])
        )
    return lines


def _category_block(
    category: str,
    items: List[NewsItem],
    bilingual: bool,
) -> List[str]:
    title = CATEGORY_NAMES.get(category, category)
    if bilingual:
        english = {
            "technology": "Technology",
            "finance": "Finance",
            "sports": "Sports",
            "society": "Society",
            "politics": "Politics",
        }.get(category, category)
        title = f"{title} / {english}"
    lines = [f"## {title}", ""]
    if not items:
        lines.extend(["今日没有达到评分阈值的新闻。", ""])
        if bilingual:
            lines.extend(["No item met today's score threshold.", ""])
        return lines

    for item in items:
        tags = "、".join(item.ai_tags[:6]) or "未标注"
        lines.extend(
            [
                f"### {item.title}",
                f"- **摘要**：{_fact_text(item)}",
                f"- **AI 分数**：{item.ai_score:.1f}/10",
                f"- **推荐理由**：{trim_text(item.ai_reason, 160)}",
                f"- **标签**：{tags}",
                f"- **来源**：{_source_line(item)}",
                "",
            ]
        )
    return lines


def build_fallback_report(
    core_topic: NewsItem,
    grouped_news: Dict[str, List[NewsItem]],
    report_date: Union[date, datetime, str],
    radar_stats: Optional[Dict[str, object]] = None,
    bilingual: bool = False,
) -> str:
    """DeepSeek 不可用时输出短小、可追溯的本地简报。"""

    date_text = _date_text(report_date)
    stats = radar_stats or {}
    selected_count = sum(len(items) for items in grouped_news.values())
    filtered_count = int(stats.get("filtered_count", 0))
    title = (
        "每日热点新闻简报 / Daily News Digest"
        if bilingual
        else "每日热点新闻简报"
    )
    lines = [
        f"# {title}｜{date_text}",
        "",
        f"> 本期精选 {selected_count} 条新闻，过滤 {filtered_count} 条低分主题。",
        "",
        "## 今日重点" + (" / Today's Highlights" if bilingual else ""),
        "",
        f"今日最值得关注的是“{core_topic.title}”。"
        "排序综合了本地规则、AI 重要性、主题聚类和个人偏好。",
    ]
    if bilingual:
        lines.extend(
            [
                "",
                f'Today\'s leading story is "{core_topic.title}". '
                "Ranking combines local rules, AI importance, clustering, "
                "and personal preferences.",
            ]
        )
    lines.extend(
        [
            "",
            "## 核心新闻" + (" / Core Story" if bilingual else ""),
            "",
            f"### {core_topic.title}",
            f"- **发生了什么**：{_fact_text(core_topic)}",
            f"- **为什么重要**：{trim_text(core_topic.ai_reason, 160)}",
        ]
    )
    lines.extend(_enrichment_lines(core_topic))
    lines.extend([f"- **来源**：{_source_line(core_topic)}", ""])

    for category in CATEGORY_ORDER:
        lines.extend(
            _category_block(
                category,
                grouped_news.get(category, []),
                bilingual,
            )
        )

    lines.extend(
        [
            "## 今日观察" + (" / Daily Observation" if bilingual else ""),
            "",
            "高分主题优先进入简报，多来源报道会获得额外权重。"
            "当前内容仅依据 RSS 标题、摘要和链接，不代表已核验新闻全文。"
            "政治内容保持中立，财经内容不构成投资建议。",
            "",
            "## 我的关注建议" + (" / Follow-up" if bilingual else ""),
            "",
        ]
    )
    suggestions = sorted(
        (
            item
            for items in grouped_news.values()
            for item in items
        ),
        key=lambda item: item.score,
        reverse=True,
    )[:3]
    lines.extend(
        f"- 后续关注 [{item.title}]({item.url}) 的可靠更新。"
        for item in suggestions
    )
    return sanitize_report("\n".join(lines).strip()) + "\n"


def _limited_grouped_news(
    grouped_news: Dict[str, List[NewsItem]],
    max_total: int,
) -> Dict[str, List[NewsItem]]:
    limited: Dict[str, List[NewsItem]] = {}
    remaining = max_total
    for category in CATEGORY_ORDER:
        if remaining <= 0:
            break
        items = grouped_news.get(category, [])
        if items:
            limited[category] = items[:remaining]
            remaining -= len(limited[category])
    for category, items in grouped_news.items():
        if remaining <= 0:
            break
        if category in limited or not items:
            continue
        limited[category] = items[:remaining]
        remaining -= len(limited[category])
    return limited


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
    """调用 DeepSeek 生成精简日报；异常时退回本地模板。"""

    del preference_profile, clusters
    bilingual = bool(
        settings.filtering.get("enable_bilingual_report", False)
    )
    max_total = max(
        1,
        int(settings.filtering.get("max_total_news", 12)),
    )
    max_top = max(
        1,
        int(settings.filtering.get("max_top_news", 8)),
    )
    limited_grouped = _limited_grouped_news(grouped_news, max_total)
    stats = radar_stats or {}
    compact_stats = {
        key: stats.get(key, 0)
        for key in (
            "fetched_count",
            "deduplicated_count",
            "eligible_count",
            "filtered_count",
            "selected_count",
        )
    }

    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        payload = {
            "report_date": _date_text(report_date),
            "language_mode": "bilingual" if bilingual else "zh-CN",
            "core_topic": news_item_to_dict(
                core_topic,
                include_enrichment=True,
            ),
            "grouped_news": {
                category: [news_item_to_dict(item) for item in items]
                for category, items in limited_grouped.items()
            },
            "top_news": [
                news_item_to_dict(item) for item in top_news[:max_top]
            ],
            "radar_stats": compact_stats,
        }

        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=120.0,
            max_retries=1,
        )
        language_request = (
            "中英文双语精简版" if bilingual else "中文精简版"
        )
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        f"请根据以下数据生成{language_request}新闻简报：\n"
                        + json.dumps(payload, ensure_ascii=False)
                    ),
                },
            ],
            temperature=0.2,
            stream=False,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("DeepSeek 返回了空内容。")
        return sanitize_report(content.strip()) + "\n"
    except Exception as exc:
        print(
            "警告：DeepSeek 日报生成失败"
            f"（{type(exc).__name__}），将生成本地 fallback 简报。"
        )
        return build_fallback_report(
            core_topic,
            limited_grouped,
            report_date,
            radar_stats=radar_stats,
            bilingual=bilingual,
        )
