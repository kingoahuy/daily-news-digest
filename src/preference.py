import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml

from src.database import (
    DEFAULT_DB_PATH,
    get_interaction_based_preferences,
    list_feedback_with_news,
    list_user_preferences,
    save_user_preference,
)
from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFERENCES_PATH = PROJECT_ROOT / "config" / "preferences.yaml"
POSITIVE_COMMENT_WORDS = (
    "重要",
    "继续关注",
    "喜欢",
    "对我有用",
    "深入分析",
    "值得追踪",
)
NEGATIVE_COMMENT_WORDS = (
    "不感兴趣",
    "以后少推",
    "无聊",
    "重复",
    "没价值",
)


def _safe_json_list(value: object) -> List[str]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return [part.strip() for part in str(value).split(",") if part.strip()]
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def load_base_preferences(
    preferences_path: Path = DEFAULT_PREFERENCES_PATH,
) -> Dict[str, object]:
    """读取用户声明的初始偏好。文件缺失时返回可用的空结构。"""

    path = Path(preferences_path)
    if not path.exists():
        return {
            "user_profile": {},
            "category_weights": {},
            "sports_weights": {},
            "finance_weights": {},
            "technology_weights": {},
        }

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"无法读取偏好配置 {path}：{exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("preferences.yaml 顶层必须是字典结构。")
    return data


def load_feedback_preferences(
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    """把历史反馈汇总为类别与关键词调整值。

    这里使用透明规则，不做黑盒机器学习。数据越多，平均评分越稳定。
    """

    rows = list_feedback_with_news(db_path)
    category_ratings: Dict[str, List[int]] = defaultdict(list)
    keyword_ratings: Dict[str, List[int]] = defaultdict(list)
    topic_counts: Dict[str, int] = defaultdict(int)

    for row in rows:
        rating = int(row["rating"])
        category = str(row.get("category") or "").strip()
        if category:
            category_ratings[category].append(rating)

        tags = _safe_json_list(row.get("tags"))
        keywords = _safe_json_list(row.get("keywords"))
        subcategory = str(row.get("subcategory") or "").strip()
        terms = list(dict.fromkeys(tags + keywords + ([subcategory] if subcategory else [])))

        for term in terms:
            keyword_ratings[term].append(rating)
            topic_counts[term] += 1

        if "值得追踪" in tags:
            for term in terms:
                keyword_ratings[term].append(2)
        if "以后少推" in tags:
            for term in terms:
                keyword_ratings[term].append(-2)

    category_adjustments: Dict[str, float] = {}
    category_averages: Dict[str, float] = {}
    for category, ratings in category_ratings.items():
        average = sum(ratings) / len(ratings)
        category_averages[category] = round(average, 3)
        if average > 1:
            category_adjustments[category] = 0.4
        elif average < -1:
            category_adjustments[category] = -0.4
        else:
            category_adjustments[category] = round(average * 0.2, 3)

    keyword_adjustments: Dict[str, float] = {}
    keyword_averages: Dict[str, float] = {}
    for keyword, ratings in keyword_ratings.items():
        average = sum(ratings) / len(ratings)
        keyword_averages[keyword] = round(average, 3)
        # 至少出现一次即可学习，但把单个关键词的影响限制在合理范围内。
        keyword_adjustments[keyword] = round(
            max(-0.8, min(0.8, average * 0.3)),
            3,
        )

    return {
        "feedback_count": len(rows),
        "category_adjustments": category_adjustments,
        "category_averages": category_averages,
        "keyword_adjustments": keyword_adjustments,
        "keyword_averages": keyword_averages,
        "topic_counts": dict(topic_counts),
    }


def load_interaction_preferences(
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    """把点赞、收藏和评论转换为透明的偏好调整值。"""

    rows = get_interaction_based_preferences(db_path)
    category_scores: Dict[str, float] = defaultdict(float)
    keyword_scores: Dict[str, float] = defaultdict(float)
    source_scores: Dict[str, float] = defaultdict(float)
    action_category_counts: Dict[str, Dict[str, int]] = {
        "like": defaultdict(int),
        "favorite": defaultdict(int),
        "comment": defaultdict(int),
    }
    comment_topic_counts: Dict[str, int] = defaultdict(int)
    positive_comments = 0
    negative_comments = 0

    for row in rows:
        action_type = str(row.get("action_type") or "")
        category = str(row.get("category") or "").strip()
        source = str(row.get("source") or "").strip()
        keywords = _safe_json_list(row.get("keywords"))
        subcategory = str(row.get("subcategory") or "").strip()
        terms = list(
            dict.fromkeys(keywords + ([subcategory] if subcategory else []))
        )

        if action_type == "like":
            weight = 1.0
        elif action_type == "favorite":
            weight = 2.0
        elif action_type == "comment":
            comment = str(
                row.get("action_value") or row.get("note") or ""
            ).strip()
            has_positive = any(word in comment for word in POSITIVE_COMMENT_WORDS)
            has_negative = any(word in comment for word in NEGATIVE_COMMENT_WORDS)
            if has_positive and not has_negative:
                weight = 1.5
                positive_comments += 1
            elif has_negative and not has_positive:
                weight = -1.5
                negative_comments += 1
            else:
                weight = 0.25
            for term in terms:
                comment_topic_counts[term] += 1
        else:
            continue

        if category:
            category_scores[category] += weight
            action_category_counts[action_type][category] += 1
        for term in terms:
            keyword_scores[term] += weight
        if source and action_type == "favorite":
            source_scores[source] += weight

    # 限制单一兴趣的最大影响，避免少量连续点击压过时效性和事实重要性。
    category_adjustments = {
        key: round(max(-1.2, min(1.2, value * 0.18)), 3)
        for key, value in category_scores.items()
    }
    keyword_adjustments = {
        key: round(max(-1.5, min(1.5, value * 0.22)), 3)
        for key, value in keyword_scores.items()
    }
    source_adjustments = {
        key: round(max(0.0, min(1.0, value * 0.15)), 3)
        for key, value in source_scores.items()
    }

    return {
        "interaction_count": len(rows),
        "category_adjustments": category_adjustments,
        "keyword_adjustments": keyword_adjustments,
        "source_adjustments": source_adjustments,
        "action_category_counts": {
            action: dict(counts)
            for action, counts in action_category_counts.items()
        },
        "comment_topic_counts": dict(comment_topic_counts),
        "positive_comment_count": positive_comments,
        "negative_comment_count": negative_comments,
    }


def build_user_preference_profile(
    preferences_path: Path = DEFAULT_PREFERENCES_PATH,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    """合并初始偏好、历史反馈和网页端手动设置。"""

    base = load_base_preferences(preferences_path)
    feedback = load_feedback_preferences(db_path)
    interactions = load_interaction_preferences(db_path)

    category_weights = {
        str(key): float(value)
        for key, value in dict(base.get("category_weights") or {}).items()
    }
    subcategory_weights: Dict[str, float] = {}
    for section in ("sports_weights", "finance_weights", "technology_weights"):
        for key, value in dict(base.get(section) or {}).items():
            subcategory_weights[str(key)] = float(value)

    manual_preferences = list_user_preferences(db_path)
    manual_keyword_weights: Dict[str, float] = {}
    for row in manual_preferences:
        key = str(row["preference_key"])
        value = str(row["preference_value"])
        weight = float(row["weight"])
        if key == "category_weight":
            category_weights[value] = weight
        elif key in {"keyword_weight", "topic_weight"}:
            manual_keyword_weights[value] = weight

    return {
        "user_profile": dict(base.get("user_profile") or {}),
        "category_weights": category_weights,
        "subcategory_weights": subcategory_weights,
        "feedback_category_adjustments": feedback["category_adjustments"],
        "feedback_keyword_adjustments": feedback["keyword_adjustments"],
        "category_averages": feedback["category_averages"],
        "keyword_averages": feedback["keyword_averages"],
        "topic_counts": feedback["topic_counts"],
        "manual_keyword_weights": manual_keyword_weights,
        "feedback_count": feedback["feedback_count"],
        "interaction_category_adjustments": interactions[
            "category_adjustments"
        ],
        "interaction_keyword_adjustments": interactions[
            "keyword_adjustments"
        ],
        "interaction_source_adjustments": interactions[
            "source_adjustments"
        ],
        "action_category_counts": interactions["action_category_counts"],
        "comment_topic_counts": interactions["comment_topic_counts"],
        "positive_comment_count": interactions["positive_comment_count"],
        "negative_comment_count": interactions["negative_comment_count"],
        "interaction_count": interactions["interaction_count"],
    }


def _text_contains(text: str, keyword: str) -> bool:
    if keyword.isascii():
        pattern = rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return keyword in text


def adjust_news_score_by_preferences(
    news_item: NewsItem,
    base_score: float,
    preference_profile: Optional[Dict[str, object]] = None,
) -> float:
    """根据可解释的用户画像调整单条新闻分数。"""

    profile = preference_profile or build_user_preference_profile()
    score = float(base_score)

    category_weights = dict(profile.get("category_weights") or {})
    category_weight = float(category_weights.get(news_item.category, 1.0))
    score += (category_weight - 1.0) * 1.5

    subcategory_weights = dict(profile.get("subcategory_weights") or {})
    if news_item.subcategory:
        subcategory_weight = float(
            subcategory_weights.get(news_item.subcategory, 1.0)
        )
        score += (subcategory_weight - 1.0) * 0.8

    category_adjustments = dict(
        profile.get("feedback_category_adjustments") or {}
    )
    score += float(category_adjustments.get(news_item.category, 0.0))
    interaction_category_adjustments = dict(
        profile.get("interaction_category_adjustments") or {}
    )
    score += float(
        interaction_category_adjustments.get(news_item.category, 0.0)
    )

    text = f"{news_item.title} {news_item.summary}"
    learned_keywords = dict(profile.get("feedback_keyword_adjustments") or {})
    manual_keywords = dict(profile.get("manual_keyword_weights") or {})
    interaction_keywords = dict(
        profile.get("interaction_keyword_adjustments") or {}
    )
    for keyword, adjustment in learned_keywords.items():
        if _text_contains(text, str(keyword)):
            score += float(adjustment)
    for keyword, weight in manual_keywords.items():
        if _text_contains(text, str(keyword)):
            score += (float(weight) - 1.0) * 0.8
    for keyword, adjustment in interaction_keywords.items():
        if _text_contains(text, str(keyword)):
            score += float(adjustment)

    source_adjustments = dict(
        profile.get("interaction_source_adjustments") or {}
    )
    score += float(source_adjustments.get(news_item.source, 0.0))

    return round(score, 3)


def save_manual_preference(
    key: str,
    value: str,
    weight: float,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    save_user_preference(
        preference_key=key,
        preference_value=value,
        weight=weight,
        source="manual",
        db_path=db_path,
    )
