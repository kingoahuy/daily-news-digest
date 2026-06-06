import re
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set

from src.config import Settings
from src.models import NewsItem


CATEGORY_WEIGHTS = {
    "finance": 1.5,
    "politics": 1.3,
    "society": 1.2,
    "technology": 1.1,
    "sports": 0.8,
}

IMPORTANT_KEYWORDS = [
    "crisis",
    "war",
    "election",
    "market",
    "AI",
    "rate",
    "inflation",
    "earnings",
    "policy",
    "Trump",
    "China",
    "US",
    "Singapore",
    "economy",
    "stock",
    "trade",
    "tariff",
    "conflict",
    "company",
    "tech",
    "sport",
    "final",
    "危机",
    "战争",
    "选举",
    "市场",
    "人工智能",
    "利率",
    "通胀",
    "财报",
    "政策",
    "中国",
    "美国",
    "新加坡",
    "经济",
    "股市",
    "贸易",
    "关税",
    "冲突",
    "公司",
    "科技",
    "体育",
    "决赛",
]


def _contains_keyword(text: str, keyword: str) -> bool:
    """英文关键词按单词匹配，中文关键词按子串匹配。"""

    if keyword.isascii():
        pattern = rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return keyword in text


def _matched_keywords(item: NewsItem) -> Set[str]:
    text = f"{item.title} {item.summary}"
    return {
        keyword.casefold() if keyword.isascii() else keyword
        for keyword in IMPORTANT_KEYWORDS
        if _contains_keyword(text, keyword)
    }


def _freshness_score(item: NewsItem, lookback_hours: int) -> float:
    if item.published_at is None:
        return 0.0

    published_at = item.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_hours = max(
        0.0,
        (datetime.now(timezone.utc) - published_at.astimezone(timezone.utc)).total_seconds()
        / 3600,
    )
    return max(0.0, 3.0 * (1.0 - age_hours / lookback_hours))


def _keyword_frequency(items: Iterable[NewsItem]) -> Counter:
    frequency: Counter = Counter()
    for item in items:
        frequency.update(_matched_keywords(item))
    return frequency


def rank_news(items: List[NewsItem], settings: Settings) -> Dict[str, object]:
    """为新闻打分、按分类筛选，并选出核心议题。"""

    if not items:
        raise ValueError(
            "没有可用新闻。请检查网络连接、RSS 地址或 NEWS_LOOKBACK_HOURS。"
        )

    keyword_frequency = _keyword_frequency(items)

    for item in items:
        matched = _matched_keywords(item)
        keyword_score = min(len(matched) * 0.55, 3.3)
        repeated_score = sum(
            min(keyword_frequency[keyword] - 1, 3) * 0.2
            for keyword in matched
            if keyword_frequency[keyword] > 1
        )
        item.score = round(
            CATEGORY_WEIGHTS.get(item.category, 1.0)
            + _freshness_score(item, settings.news_lookback_hours)
            + keyword_score
            + repeated_score,
            3,
        )

    grouped_news: Dict[str, List[NewsItem]] = {}
    categories = list(CATEGORY_WEIGHTS)
    categories.extend(
        category
        for category in {item.category for item in items}
        if category not in CATEGORY_WEIGHTS
    )

    for category in categories:
        category_items = sorted(
            (item for item in items if item.category == category),
            key=lambda item: (
                item.score,
                item.published_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
        if category_items:
            grouped_news[category] = category_items[
                : settings.max_news_per_category
            ]

    selected_items = [
        item for category_items in grouped_news.values() for item in category_items
    ]
    # 全局头条只保留前 10 条，避免与分类数据重复过多、浪费模型上下文。
    top_news = sorted(
        selected_items, key=lambda item: item.score, reverse=True
    )[:10]
    core_topic = top_news[0]

    return {
        "core_topic": core_topic,
        "grouped_news": grouped_news,
        "top_news": top_news,
    }
