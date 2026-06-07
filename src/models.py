from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class NewsItem:
    """一条从 RSS 中提取的新闻。"""

    title: str  # 新闻标题
    summary: str  # RSS 提供的摘要，不包含新闻全文
    url: str  # 新闻原始链接
    source: str  # RSS 来源名称
    category: str  # 新闻分类
    published_at: Optional[datetime]  # 发布时间，RSS 未提供时为 None
    subcategory: str = ""  # 根据关键词识别的细分类
    score: float = 0.0  # 综合排序分数，由 ranker 模块计算
    rule_score: float = 0.0
    ai_score: float = 0.0
    ai_reason: str = ""
    ai_summary: str = ""
    ai_tags: List[str] = field(default_factory=list)
    importance_tier: str = "low"
    cluster_id: str = ""
    cluster_title: str = ""
    enrichment: Dict[str, object] = field(default_factory=dict)
    preference_adjustment: float = 0.0
