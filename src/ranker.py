import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Set

from src.config import Settings
from src.deduplicator import StoryCluster
from src.models import NewsItem
from src.preference import (
    adjust_news_score_by_preferences,
    build_user_preference_profile,
    load_base_preferences,
)


DEFAULT_CATEGORY_WEIGHTS = {
    "technology": 1.5,
    "finance": 1.5,
    "sports": 1.4,
    "society": 1.2,
    "politics": 1.2,
}

# 每个标准关键词可以对应中英文多种写法。保存进数据库时使用字典键，
# 这样后续反馈学习不会因为大小写或译名不同而被拆散。
KEYWORD_ALIASES = {
    "AI": ["AI", "人工智能"],
    "大模型": ["大模型", "LLM", "large language model"],
    "DeepSeek": ["DeepSeek", "深度求索"],
    "OpenAI": ["OpenAI", "ChatGPT"],
    "NVIDIA": ["NVIDIA", "英伟达"],
    "半导体": ["半导体", "芯片", "semiconductor", "chip"],
    "新能源": ["新能源", "电动车", "electric vehicle", "EV"],
    "机器人": ["机器人", "robot", "robotics"],
    "消费电子": ["消费电子", "smartphone", "智能手机"],
    "互联网公司": ["互联网公司", "platform company", "big tech"],
    "美股": ["美股", "Wall Street", "S&P 500", "Nasdaq", "纳斯达克"],
    "A股": ["A股", "上证", "深证", "沪指"],
    "港股": ["港股", "恒生指数", "Hang Seng"],
    "股市": ["股市", "股票", "stock market", "shares"],
    "利率": ["利率", "interest rate", "rate cut", "rate hike"],
    "通胀": ["通胀", "inflation", "CPI"],
    "财报": ["财报", "earnings", "revenue", "profit"],
    "并购": ["并购", "acquisition", "merger"],
    "斯诺克": ["斯诺克", "snooker"],
    "丁俊晖": ["丁俊晖", "Ding Junhui"],
    "奥沙利文": ["奥沙利文", "O'Sullivan", "Ronnie O"],
    "特鲁姆普": ["特鲁姆普", "Judd Trump"],
    "网球": ["网球", "tennis", "ATP", "WTA"],
    "德约科维奇": ["德约科维奇", "Djokovic"],
    "纳达尔": ["纳达尔", "Nadal"],
    "辛纳": ["辛纳", "Sinner"],
    "阿尔卡拉斯": ["阿尔卡拉斯", "Alcaraz"],
    "乒乓球": ["乒乓球", "国乒", "table tennis", "WTT"],
    "NBA": ["NBA"],
    "湖人": ["湖人", "Lakers"],
    "勇士": ["勇士", "Warriors"],
    "凯尔特人": ["凯尔特人", "Celtics"],
    "足球": ["足球", "football", "soccer"],
    "欧冠": ["欧冠", "Champions League", "UCL"],
    "英超": ["英超", "Premier League"],
    "西甲": ["西甲", "La Liga"],
    "中超": ["中超", "Chinese Super League"],
    "中国": ["中国", "China", "Chinese"],
    "美国": ["美国", "United States", "U.S.", "US"],
    "新加坡": ["新加坡", "Singapore"],
    "选举": ["选举", "election"],
    "政策": ["政策", "policy", "regulation"],
    "贸易": ["贸易", "trade", "tariff", "关税"],
    "冲突": ["冲突", "war", "conflict"],
    "公共安全": ["公共安全", "public safety"],
    "教育": ["教育", "education"],
    "就业": ["就业", "employment", "jobs"],
    "医疗": ["医疗", "healthcare", "hospital"],
    "灾害": ["灾害", "earthquake", "flood", "wildfire"],
}

SUBCATEGORY_RULES = {
    "technology": {
        "ai": ["AI", "大模型", "DeepSeek", "OpenAI"],
        "llm": ["大模型", "DeepSeek", "OpenAI"],
        "semiconductor": ["半导体", "NVIDIA"],
        "new_energy": ["新能源"],
        "robotics": ["机器人"],
        "consumer_electronics": ["消费电子"],
        "internet_companies": ["互联网公司"],
    },
    "finance": {
        "stock_market": ["美股", "A股", "港股", "股市"],
        "hot_industries": ["新能源", "半导体", "AI"],
        "ai_industry": ["AI", "大模型", "DeepSeek", "OpenAI", "NVIDIA"],
        "semiconductor": ["半导体", "NVIDIA"],
        "new_energy": ["新能源"],
        "company_earnings": ["财报"],
        "mergers": ["并购"],
    },
    "sports": {
        "snooker": ["斯诺克", "丁俊晖", "奥沙利文", "特鲁姆普"],
        "tennis": ["网球", "德约科维奇", "纳达尔", "辛纳", "阿尔卡拉斯"],
        "table_tennis": ["乒乓球"],
        "nba": ["NBA", "湖人", "勇士", "凯尔特人"],
        "football": ["足球", "欧冠", "英超", "西甲", "中超"],
    },
    "society": {
        "public_safety": ["公共安全"],
        "education": ["教育"],
        "employment": ["就业"],
        "healthcare": ["医疗"],
        "disaster": ["灾害"],
    },
    "politics": {
        "china": ["中国"],
        "united_states": ["美国"],
        "singapore": ["新加坡"],
        "election": ["选举"],
        "policy": ["政策"],
        "trade": ["贸易"],
        "conflict": ["冲突"],
    },
}


def _contains_keyword(text: str, keyword: str) -> bool:
    if keyword.isascii():
        pattern = rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return keyword in text


def extract_keywords(item: NewsItem) -> Set[str]:
    text = f"{item.title} {item.summary}"
    return {
        standard_name
        for standard_name, aliases in KEYWORD_ALIASES.items()
        if any(_contains_keyword(text, alias) for alias in aliases)
    }


def _assign_subcategory(item: NewsItem, matched: Set[str]) -> str:
    rules = SUBCATEGORY_RULES.get(item.category, {})
    best_name = ""
    best_count = 0
    for name, keywords in rules.items():
        count = len(set(keywords) & matched)
        if count > best_count:
            best_name = name
            best_count = count
    return best_name


def _freshness_score(item: NewsItem) -> float:
    if item.published_at is None:
        return 0.0

    published_at = item.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_hours = max(
        0.0,
        (
            datetime.now(timezone.utc)
            - published_at.astimezone(timezone.utc)
        ).total_seconds()
        / 3600,
    )
    if age_hours <= 24:
        return 3.0 - (age_hours / 24 * 1.5)
    if age_hours <= 48:
        return 1.5 - ((age_hours - 24) / 24 * 1.5)
    return -1.0


def _keyword_sources(
    items: Iterable[NewsItem],
) -> Dict[str, Set[str]]:
    sources: Dict[str, Set[str]] = defaultdict(set)
    for item in items:
        for keyword in extract_keywords(item):
            sources[keyword].add(item.source)
    return sources


def _load_profile(settings: Settings) -> Dict[str, object]:
    try:
        return build_user_preference_profile(
            preferences_path=settings.preferences_path,
            db_path=settings.database_path,
        )
    except Exception as exc:
        print(
            f"警告：历史偏好读取失败（{type(exc).__name__}），"
            "本次仅使用 preferences.yaml。"
        )
        base = load_base_preferences(settings.preferences_path)
        return {
            "category_weights": base.get("category_weights", {}),
            "subcategory_weights": {
                key: value
                for section in (
                    "sports_weights",
                    "finance_weights",
                    "technology_weights",
                )
                for key, value in dict(base.get(section) or {}).items()
            },
        }


def score_news_by_rules(
    items: List[NewsItem],
    settings: Settings,
) -> Dict[str, List[str]]:
    """只计算可解释的本地规则分，不应用历史偏好。"""

    if not items:
        raise ValueError(
            "没有可用新闻。请检查网络连接、RSS 地址或时间窗口配置。"
        )

    configured_weights = dict(
        settings.filtering.get("category_weights") or {}
    )
    category_weights = {
        **DEFAULT_CATEGORY_WEIGHTS,
        **{
            str(key): float(value)
            for key, value in configured_weights.items()
        },
    }
    keyword_sources = _keyword_sources(items)
    keyword_map: Dict[str, List[str]] = {}

    for item in items:
        matched = extract_keywords(item)
        keyword_map[item.url] = sorted(matched)
        item.subcategory = _assign_subcategory(item, matched)

        category_score = category_weights.get(item.category, 1.0)
        keyword_score = min(len(matched) * 0.45, 3.6)
        multi_source_score = sum(
            min(len(keyword_sources[keyword]) - 1, 3) * 0.25
            for keyword in matched
            if len(keyword_sources[keyword]) > 1
        )
        item.rule_score = round(
            max(
                0.0,
                min(
                    category_score
                    + _freshness_score(item)
                    + keyword_score
                    + min(multi_source_score, 2.0),
                    10.0,
                ),
            ),
            3,
        )
        item.score = item.rule_score
    return keyword_map


def rank_news(
    items: List[NewsItem],
    settings: Settings,
    preference_profile: Optional[Dict[str, object]] = None,
    clusters: Optional[List[StoryCluster]] = None,
    keyword_map: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, object]:
    """综合规则分、AI 分、主题簇和历史反馈完成最终排序。"""

    if not items:
        raise ValueError(
            "没有可用新闻。请检查网络连接、RSS 地址或 NEWS_LOOKBACK_HOURS。"
        )

    profile = preference_profile or _load_profile(settings)
    keyword_map = keyword_map or score_news_by_rules(items, settings)
    cluster_map = {
        cluster.cluster_id: cluster for cluster in (clusters or [])
    }
    representatives = (
        [cluster.representative_item for cluster in clusters]
        if clusters
        else items
    )

    for item in representatives:
        ai_score = item.ai_score or item.rule_score
        base_score = (ai_score * 0.72) + (item.rule_score * 0.28)
        cluster = cluster_map.get(item.cluster_id)
        if cluster:
            base_score += max(0.0, cluster.cluster_score - ai_score)
        personalized = adjust_news_score_by_preferences(
            item,
            base_score,
            profile,
        )
        item.preference_adjustment = round(personalized - base_score, 3)
        item.score = personalized

    categories = list(DEFAULT_CATEGORY_WEIGHTS)
    categories.extend(
        sorted(
            category
            for category in {item.category for item in representatives}
            if category not in DEFAULT_CATEGORY_WEIGHTS
        )
    )

    threshold = float(settings.filtering.get("ai_score_threshold", 6.5))
    eligible = [
        item
        for item in representatives
        if (item.ai_score or item.rule_score) >= threshold
        and item.importance_tier != "noise"
    ]
    if not eligible:
        eligible = sorted(
            representatives,
            key=lambda item: item.score,
            reverse=True,
        )[:1]

    max_per_category = max(
        1,
        int(settings.filtering.get("max_items_per_category", 3)),
    )
    max_total_news = max(
        1,
        int(settings.filtering.get("max_total_news", 12)),
    )
    max_top_news = max(
        1,
        int(settings.filtering.get("max_top_news", 8)),
    )
    candidates_by_category: Dict[str, List[NewsItem]] = {}
    for category in categories:
        category_items = sorted(
            (item for item in eligible if item.category == category),
            key=lambda item: (
                item.score,
                item.published_at
                or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
        if category_items:
            candidates_by_category[category] = category_items

    selected_items: List[NewsItem] = []
    selected_urls = set()
    category_counts = {category: 0 for category in categories}

    # 先为每个有高分条目的分类保留一条，再按综合分补足总量。
    for category in categories:
        category_items = candidates_by_category.get(category, [])
        if not category_items or len(selected_items) >= max_total_news:
            continue
        item = category_items[0]
        selected_items.append(item)
        selected_urls.add(item.url)
        category_counts[category] += 1

    for item in sorted(eligible, key=lambda row: row.score, reverse=True):
        if len(selected_items) >= max_total_news:
            break
        if item.url in selected_urls:
            continue
        if category_counts.get(item.category, 0) >= max_per_category:
            continue
        selected_items.append(item)
        selected_urls.add(item.url)
        category_counts[item.category] = (
            category_counts.get(item.category, 0) + 1
        )

    grouped_news: Dict[str, List[NewsItem]] = {}
    for category in categories:
        category_items = sorted(
            (
                item
                for item in selected_items
                if item.category == category
            ),
            key=lambda item: item.score,
            reverse=True,
        )
        if category_items:
            grouped_news[category] = category_items

    top_news = sorted(
        selected_items,
        key=lambda item: item.score,
        reverse=True,
    )[:max_top_news]
    if not top_news:
        raise ValueError("评分过滤后没有可用于生成日报的新闻。")
    core_topic = top_news[0]
    category_averages = {}
    for category in categories:
        scores = [
            item.ai_score or item.rule_score
            for item in representatives
            if item.category == category
        ]
        if scores:
            category_averages[category] = round(
                sum(scores) / len(scores),
                2,
            )
    preference_adjustments = [
        item.preference_adjustment for item in representatives
    ]

    return {
        "core_topic": core_topic,
        "grouped_news": grouped_news,
        "top_news": top_news,
        "keyword_map": keyword_map,
        "preference_profile": profile,
        "filtered_count": len(representatives) - len(eligible),
        "eligible_count": len(eligible),
        "representative_count": len(representatives),
        "selected_count": len(selected_items),
        "category_averages": category_averages,
        "preference_impact": {
            "average_adjustment": round(
                sum(preference_adjustments) / len(preference_adjustments),
                3,
            )
            if preference_adjustments
            else 0.0,
            "boosted_items": sum(
                1 for value in preference_adjustments if value > 0.01
            ),
            "reduced_items": sum(
                1 for value in preference_adjustments if value < -0.01
            ),
        },
    }
