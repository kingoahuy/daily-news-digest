import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha1
from typing import Dict, Iterable, List, Set
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.models import NewsItem


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ocid",
    "ref",
    "ref_src",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "says",
    "that",
    "the",
    "to",
    "with",
    "after",
    "new",
    "latest",
}


@dataclass
class StoryCluster:
    cluster_id: str
    main_title: str
    representative_item: NewsItem
    related_items: List[NewsItem]
    sources: List[str]
    categories: List[str]
    cluster_score: float


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    hostname = (parts.hostname or "").casefold()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    port = f":{parts.port}" if parts.port else ""
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in TRACKING_PARAMETERS
    ]
    path = re.sub(r"/+$", "", parts.path) or "/"
    return urlunsplit(
        (
            parts.scheme.casefold() or "https",
            hostname + port,
            path,
            urlencode(sorted(query)),
            "",
        )
    )


def normalize_title(title: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", title.casefold())
    return re.sub(r"\s+", " ", text).strip()


def title_keywords(title: str) -> Set[str]:
    tokens: Set[str] = set()
    for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", title.casefold()):
        if re.fullmatch(r"[\u4e00-\u9fff]{2,}", token):
            if len(token) <= 4:
                tokens.add(token)
            tokens.update(token[index : index + 2] for index in range(len(token) - 1))
        elif len(token) >= 3 and token not in STOP_WORDS:
            tokens.add(token)
    return tokens


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()


def _keyword_overlap(left: str, right: str) -> tuple[int, float]:
    left_words = title_keywords(left)
    right_words = title_keywords(right)
    if not left_words or not right_words:
        return 0, 0.0
    common = left_words & right_words
    return len(common), len(common) / min(len(left_words), len(right_words))


def _richer_item(left: NewsItem, right: NewsItem) -> NewsItem:
    left_value = len(left.summary or "") + (5 if left.published_at else 0)
    right_value = len(right.summary or "") + (5 if right.published_at else 0)
    return left if left_value >= right_value else right


def deduplicate_news(items: Iterable[NewsItem]) -> List[NewsItem]:
    """按规范化 URL 和高置信度标题相似度去重。"""

    url_items: Dict[str, NewsItem] = {}
    for item in items:
        key = normalize_url(item.url)
        if key in url_items:
            url_items[key] = _richer_item(url_items[key], item)
        else:
            url_items[key] = item

    deduplicated: List[NewsItem] = []
    for item in url_items.values():
        duplicate_index = None
        for index, existing in enumerate(deduplicated):
            if item.category != existing.category:
                continue
            common, overlap = _keyword_overlap(item.title, existing.title)
            if _similarity(item.title, existing.title) >= 0.94 or (
                common >= 4 and overlap >= 0.88
            ):
                duplicate_index = index
                break
        if duplicate_index is None:
            deduplicated.append(item)
        else:
            deduplicated[duplicate_index] = _richer_item(
                deduplicated[duplicate_index],
                item,
            )
    return deduplicated


def _same_story(left: NewsItem, right: NewsItem) -> bool:
    common, overlap = _keyword_overlap(left.title, right.title)
    ratio = _similarity(left.title, right.title)
    return ratio >= 0.78 or (common >= 3 and overlap >= 0.55)


def cluster_news(items: Iterable[NewsItem]) -> List[StoryCluster]:
    """以标题相似度和关键词形成轻量 story clusters。"""

    ordered = sorted(
        items,
        key=lambda item: (item.ai_score, item.rule_score),
        reverse=True,
    )
    groups: List[List[NewsItem]] = []
    for item in ordered:
        target = None
        for group in groups:
            if _same_story(item, group[0]):
                target = group
                break
        if target is None:
            groups.append([item])
        else:
            target.append(item)

    clusters: List[StoryCluster] = []
    for group in groups:
        representative = group[0]
        sources = sorted({item.source for item in group if item.source})
        categories = sorted({item.category for item in group if item.category})
        cluster_id = "story-" + sha1(
            normalize_title(representative.title).encode("utf-8")
        ).hexdigest()[:12]
        source_bonus = min(max(len(sources) - 1, 0) * 0.35, 1.4)
        cluster_score = round(
            min(10.0, representative.ai_score + source_bonus),
            2,
        )
        cluster = StoryCluster(
            cluster_id=cluster_id,
            main_title=representative.title,
            representative_item=representative,
            related_items=group[1:],
            sources=sources,
            categories=categories,
            cluster_score=cluster_score,
        )
        for member in group:
            member.cluster_id = cluster_id
            member.cluster_title = representative.title
        clusters.append(cluster)
    return clusters


def cluster_to_dict(cluster: StoryCluster) -> Dict[str, object]:
    return {
        "cluster_id": cluster.cluster_id,
        "main_title": cluster.main_title,
        "representative_url": cluster.representative_item.url,
        "related_count": len(cluster.related_items),
        "sources": cluster.sources,
        "categories": cluster.categories,
        "cluster_score": cluster.cluster_score,
        "related_items": [
            {
                "title": item.title,
                "url": item.url,
                "source": item.source,
            }
            for item in cluster.related_items
        ],
    }
