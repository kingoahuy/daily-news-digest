from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    """一条从 RSS 中提取的新闻。"""

    title: str  # 新闻标题
    summary: str  # RSS 提供的摘要，不包含新闻全文
    url: str  # 新闻原始链接
    source: str  # RSS 来源名称
    category: str  # 新闻分类
    published_at: Optional[datetime]  # 发布时间，RSS 未提供时为 None
    score: float = 0.0  # 排序分数，由 ranker 模块计算
