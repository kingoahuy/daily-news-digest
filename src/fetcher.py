import calendar
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import feedparser
import yaml
from bs4 import BeautifulSoup

from src.config import Settings
from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEEDS_PATH = PROJECT_ROOT / "config" / "feeds.yaml"


def _clean_html(value: str) -> str:
    """删除 RSS 摘要中的 HTML，并压缩多余空白。"""

    text = BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _parse_published_at(entry: Any) -> Optional[datetime]:
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed_time:
        return None

    try:
        timestamp = calendar.timegm(parsed_time)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OverflowError, TypeError, ValueError):
        return None


def _load_feeds(feeds_path: Path) -> Dict[str, List[Dict[str, str]]]:
    try:
        with feeds_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"无法读取 RSS 配置文件 {feeds_path}：{exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("RSS 配置格式错误：顶层必须按分类组织。")
    return data


def _normalized_key(item: NewsItem) -> Tuple[str, str]:
    normalized_title = re.sub(r"\s+", " ", item.title).strip().casefold()
    normalized_url = item.url.strip().rstrip("/").casefold()
    return normalized_title, normalized_url


def fetch_news(
    settings: Settings, feeds_path: Path = DEFAULT_FEEDS_PATH
) -> List[NewsItem]:
    """抓取全部 RSS；单个来源失败时记录警告并继续。"""

    feeds = _load_feeds(feeds_path)
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.news_lookback_hours
    )
    collected: List[NewsItem] = []

    for category, sources in feeds.items():
        if not isinstance(sources, list):
            print(f"警告：分类 {category} 的配置不是列表，已跳过。")
            continue

        for source_config in sources:
            name = str(source_config.get("name", "")).strip()
            url = str(source_config.get("url", "")).strip()
            if not name or not url:
                print(f"警告：分类 {category} 中有 RSS 源缺少 name 或 url，已跳过。")
                continue

            print(f"正在抓取：{name}")
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                print(f"警告：RSS 源 {name} 抓取失败：{exc}")
                continue

            entries = list(getattr(feed, "entries", []) or [])
            if getattr(feed, "bozo", False):
                error = getattr(feed, "bozo_exception", "未知解析错误")
                print(f"警告：RSS 源 {name} 返回了解析警告：{error}")
                if not entries:
                    continue

            source_count = 0
            for entry in entries:
                title = _clean_html(str(entry.get("title", "")))
                link = str(entry.get("link", "")).strip()
                if not title or not link:
                    continue

                published_at = _parse_published_at(entry)
                if published_at is not None and published_at < cutoff:
                    continue

                raw_summary = entry.get("summary") or entry.get("description") or ""
                collected.append(
                    NewsItem(
                        title=title,
                        summary=_clean_html(str(raw_summary)),
                        url=link,
                        source=name,
                        category=str(category),
                        published_at=published_at,
                    )
                )
                source_count += 1

            print(f"{name} 在时间范围内抓到 {source_count} 条新闻。")

    print(f"总共抓到 {len(collected)} 条新闻。")

    deduplicated: List[NewsItem] = []
    seen: Set[Tuple[str, str]] = set()
    for item in collected:
        key = _normalized_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(item)

    print(f"去重后剩余 {len(deduplicated)} 条新闻。")
    return deduplicated
