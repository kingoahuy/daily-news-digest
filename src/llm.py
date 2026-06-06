import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Union

from openai import OpenAI

from src.config import Settings
from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "daily_report_prompt.txt"
CATEGORY_NAMES = {
    "finance": "财经",
    "politics": "政治",
    "society": "社会",
    "sports": "体育",
    "technology": "科技/商业",
}
CATEGORY_ORDER = ["finance", "politics", "society", "sports", "technology"]


def news_item_to_dict(item: NewsItem) -> Dict[str, object]:
    """把 NewsItem 转成可安全传给大模型的 JSON 数据。"""

    return {
        "title": item.title,
        "summary": item.summary,
        "url": item.url,
        "source": item.source,
        "category": item.category,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "score": item.score,
    }


def _date_text(report_date: Union[date, datetime, str]) -> str:
    if isinstance(report_date, (date, datetime)):
        return report_date.strftime("%Y-%m-%d")
    return str(report_date)


def build_fallback_report(
    core_topic: NewsItem,
    grouped_news: Dict[str, List[NewsItem]],
    report_date: Union[date, datetime, str],
) -> str:
    """API 不可用时，根据 RSS 数据生成简版中文 Markdown 日报。"""

    date_text = _date_text(report_date)
    lines = [
        f"# 今日早间热点新闻日报｜{date_text}",
        "",
        "## 开场",
        "",
        f"今天值得优先关注的是“{core_topic.title}”。"
        "以下内容仅根据当前 RSS 标题和摘要整理，未读取新闻全文。",
        "",
        "## 今日核心议题",
        "",
        "### 发生了什么",
        "",
        core_topic.summary
        or f"RSS 当前只提供了标题“{core_topic.title}”，暂时没有更多摘要信息。",
        "",
        "### 为什么重要",
        "",
        f"这条新闻在本次抓取结果中综合得分最高，来源为 {core_topic.source}。"
        "根据当前 RSS 摘要信息，暂不能判断更多细节。",
        "",
        "### 可能影响",
        "",
        "其具体影响仍需等待更多可靠信息确认。"
        "建议结合后续公开报道，观察相关市场、行业或社会层面的变化。",
        "",
        "### 后续看点",
        "",
        "- 是否出现更多来源的独立确认",
        "- 相关机构、企业或当事方是否发布正式说明",
        "- 事件是否产生可观察的市场或政策变化",
        "",
        "## 其他重要新闻",
        "",
    ]

    ordered_categories = [
        category for category in CATEGORY_ORDER if category in grouped_news
    ]
    ordered_categories.extend(
        category for category in grouped_news if category not in CATEGORY_ORDER
    )

    for category in ordered_categories:
        items = grouped_news[category]
        lines.extend([f"### {CATEGORY_NAMES.get(category, category)}", ""])
        for item in items:
            if item.url == core_topic.url and item.title == core_topic.title:
                continue
            fact = item.summary or "RSS 未提供摘要。"
            lines.append(
                f"- **{item.title}**：{fact} "
                f"影响仍需结合后续信息观察。（来源：{item.source}）"
            )
        if len(lines) >= 2 and lines[-1] == "":
            continue
        lines.append("")

    lines.extend(
        [
            "## 今日观察",
            "",
            "今天的新闻线索覆盖多个领域，但仅凭 RSS 标题和摘要不足以作出确定判断。"
            "核心议题获得了较高的时效性和关键词评分，值得继续追踪。"
            "对于尚未得到多来源支持的信息，应保持谨慎。",
            "",
            "## 信息来源",
            "",
        ]
    )

    seen_urls = set()
    for items in grouped_news.values():
        for item in items:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            lines.append(f"- [{item.title}]({item.url}) — {item.source}")

    return "\n".join(lines).strip() + "\n"


def generate_daily_report(
    settings: Settings,
    core_topic: NewsItem,
    grouped_news: Dict[str, List[NewsItem]],
    top_news: List[NewsItem],
    report_date: Union[date, datetime, str],
) -> str:
    """调用 DeepSeek 生成日报；任何 API 异常都会退回简版日报。"""

    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        payload = {
            "report_date": _date_text(report_date),
            "core_topic": news_item_to_dict(core_topic),
            "grouped_news": {
                category: [news_item_to_dict(item) for item in items]
                for category, items in grouped_news.items()
            },
            "top_news": [news_item_to_dict(item) for item in top_news],
        }

        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=45.0,
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "请根据以下 RSS 数据生成今日新闻日报：\n"
                    + json.dumps(payload, ensure_ascii=False, indent=2),
                },
            ],
            temperature=0.4,
            stream=False,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("DeepSeek 返回了空内容。")
        return content.strip() + "\n"
    except Exception as exc:
        # 不直接打印异常正文，避免第三方服务在错误信息中回显密钥片段。
        print(
            "警告：DeepSeek API 调用失败"
            f"（{type(exc).__name__}），将生成 fallback 简版日报。"
        )
        return build_fallback_report(core_topic, grouped_news, report_date)
