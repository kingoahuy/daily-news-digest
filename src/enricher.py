import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from src.config import Settings
from src.deduplicator import StoryCluster
from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "news_enrichment_prompt.txt"
REQUIRED_FIELDS = {
    "whats_new",
    "why_it_matters",
    "background",
    "possible_impact",
    "follow_up_points",
}


def _parse_json_object(content: str) -> Dict[str, object]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("背景补充结果必须是 JSON 对象。")
    return parsed


def _fallback_enrichment(item: NewsItem) -> Dict[str, object]:
    fact = item.ai_summary or item.summary or item.title
    insufficient = "根据当前摘要信息，暂不能判断更多细节。"
    return {
        "whats_new": f"当前 RSS 信息显示：{fact}",
        "why_it_matters": insufficient,
        "background": insufficient,
        "possible_impact": (
            "可能影响仍需后续可靠来源确认；财经内容不构成投资建议。"
        ),
        "follow_up_points": [
            "是否有更多独立来源确认？",
            "相关机构是否发布正式信息？",
            "后续是否出现可核实的影响？",
        ],
        "fallback": True,
    }


def _validated_result(result: Dict[str, object]) -> Dict[str, object]:
    if not REQUIRED_FIELDS.issubset(result):
        raise ValueError("背景补充缺少必要字段。")
    points = result.get("follow_up_points")
    if not isinstance(points, list):
        raise ValueError("follow_up_points 必须是数组。")
    clean = {
        key: str(result.get(key, "")).strip()
        for key in REQUIRED_FIELDS - {"follow_up_points"}
    }
    clean["follow_up_points"] = [
        str(point).strip() for point in points if str(point).strip()
    ][:5]
    clean["fallback"] = False
    return clean


def enrich_core_news(
    items: List[NewsItem],
    settings: Settings,
    clusters: Optional[List[StoryCluster]] = None,
) -> Dict[str, int]:
    """只补充最重要的 1-3 条新闻，失败时保存保守 fallback。"""

    if not items:
        return {"selected": 0, "enriched": 0, "fallback": 0}
    filtering = settings.filtering
    if not bool(filtering.get("enable_enrichment", True)):
        print("核心新闻背景补充已关闭。")
        return {"selected": 0, "enriched": 0, "fallback": 0}

    limit = max(1, min(int(filtering.get("max_enriched_items", 3)), 3))
    threshold = float(filtering.get("core_topic_threshold", 7.5))
    max_retries = max(
        1,
        min(int(filtering.get("ai_max_retries", 2)), 3),
    )
    candidates = [item for item in items if item.ai_score >= threshold][:limit]
    if not candidates:
        candidates = items[:1]

    cluster_map = {
        cluster.cluster_id: cluster for cluster in (clusters or [])
    }
    if not settings.deepseek_api_key:
        for item in candidates:
            item.enrichment = _fallback_enrichment(item)
        print("未配置 DeepSeek API Key，核心新闻使用保守背景模板。")
        return {
            "selected": len(candidates),
            "enriched": 0,
            "fallback": len(candidates),
        }

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=90.0,
        max_retries=0,
    )
    enriched = 0
    for item in candidates:
        cluster = cluster_map.get(item.cluster_id)
        payload = {
            "title": item.title,
            "summary": (item.summary or "")[:500],
            "source": item.source,
            "url": item.url,
            "category": item.category,
            "published_at": (
                item.published_at.isoformat() if item.published_at else None
            ),
            "ai_score": item.ai_score,
            "cluster_sources": cluster.sources if cluster else [item.source],
            "related_titles": (
                [related.title for related in cluster.related_items]
                if cluster
                else []
            ),
        }
        completed = False
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=settings.deepseek_model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": json.dumps(
                                payload,
                                ensure_ascii=False,
                                indent=2,
                            ),
                        },
                    ],
                    temperature=0.0,
                    stream=False,
                )
                content = response.choices[0].message.content or ""
                item.enrichment = _validated_result(
                    _parse_json_object(content)
                )
                enriched += 1
                completed = True
                break
            except Exception as exc:
                print(
                    f"警告：核心新闻背景补充第 {attempt} 次失败"
                    f"（{type(exc).__name__}）。"
                )
                if attempt < max_retries:
                    time.sleep(min(2 ** (attempt - 1), 4))
        if not completed:
            item.enrichment = _fallback_enrichment(item)

    fallback = len(candidates) - enriched
    print(
        f"核心新闻背景补充完成：选择 {len(candidates)} 条，"
        f"AI 成功 {enriched} 条，保守回退 {fallback} 条。"
    )
    return {
        "selected": len(candidates),
        "enriched": enriched,
        "fallback": fallback,
    }
