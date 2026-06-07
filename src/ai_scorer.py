import json
import re
import time
from hashlib import sha1
from pathlib import Path
from typing import Dict, Iterable, List

from openai import OpenAI

from src.config import Settings
from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "news_scoring_prompt.txt"
VALID_TIERS = {"high", "medium", "low", "noise"}


def importance_tier(score: float) -> str:
    if score >= 8:
        return "high"
    if score >= 6:
        return "medium"
    if score >= 3:
        return "low"
    return "noise"


def _item_id(item: NewsItem) -> str:
    return sha1(item.url.encode("utf-8")).hexdigest()[:16]


def _clamp_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return round(max(0.0, min(score, 10.0)), 2)


def _fallback(item: NewsItem, reason: str) -> None:
    score = _clamp_score(item.rule_score or item.score)
    fact = item.summary or item.title
    item.ai_score = score
    item.ai_reason = reason
    item.ai_summary = fact
    item.ai_tags = []
    item.importance_tier = importance_tier(score)


def apply_rule_only_score(item: NewsItem) -> None:
    """为未进入 AI 候选池的新闻保留可解释的本地规则分。"""

    _fallback(item, "未进入 AI 精评，使用本地规则评分。")


def _extract_json_array(content: str) -> List[Dict[str, object]]:
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if isinstance(parsed, dict):
        parsed = parsed.get("items") or parsed.get("results") or []
    if not isinstance(parsed, list):
        raise ValueError("AI 评分结果必须是 JSON 数组。")
    return [row for row in parsed if isinstance(row, dict)]


def _payload(items: Iterable[NewsItem]) -> List[Dict[str, object]]:
    return [
        {
            "id": _item_id(item),
            "title": item.title,
            "summary": (item.summary or "")[:500],
            "source": item.source,
            "category": item.category,
            "published_at": (
                item.published_at.isoformat() if item.published_at else None
            ),
            "rule_score": item.rule_score,
        }
        for item in items
    ]


def _apply_results(
    batch: List[NewsItem],
    results: List[Dict[str, object]],
) -> int:
    result_map = {str(row.get("id", "")): row for row in results}
    applied = 0
    for item in batch:
        row = result_map.get(_item_id(item))
        if not row:
            _fallback(
                item,
                "AI 未返回该条结果，已使用规则评分。",
            )
            continue
        score = _clamp_score(row.get("ai_score"))
        tier = str(row.get("importance_tier", "")).strip().lower()
        item.ai_score = score
        item.ai_reason = str(row.get("ai_reason", "")).strip()
        item.ai_summary = str(row.get("ai_summary", "")).strip()
        raw_tags = row.get("ai_tags") or []
        item.ai_tags = [
            str(tag).strip()
            for tag in raw_tags
            if str(tag).strip()
        ][:8]
        item.importance_tier = (
            tier if tier in VALID_TIERS else importance_tier(score)
        )
        if not item.ai_reason:
            item.ai_reason = "AI 已完成评分，但没有返回推荐理由。"
        if not item.ai_summary:
            fact = item.summary or item.title
            item.ai_summary = fact
        applied += 1
    return applied


def score_news_with_ai(
    items: List[NewsItem],
    settings: Settings,
) -> Dict[str, object]:
    """批量执行重要性评分；任何失败都回退到规则分。"""

    if not items:
        return {"total": 0, "ai_scored": 0, "fallback": 0, "batches": 0}

    filtering = settings.filtering
    enabled = bool(filtering.get("enable_ai_scoring", True))
    batch_size = max(1, min(int(filtering.get("ai_batch_size", 10)), 10))
    max_retries = max(1, min(int(filtering.get("ai_max_retries", 3)), 3))
    if not enabled or not settings.deepseek_api_key:
        reason = (
            "AI 评分已关闭，使用规则评分。"
            if not enabled
            else "未配置 DeepSeek API Key，使用规则评分。"
        )
        for item in items:
            _fallback(item, reason)
        print(f"AI 新闻评分跳过：{reason}")
        return {
            "total": len(items),
            "ai_scored": 0,
            "fallback": len(items),
            "batches": 0,
        }

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=90.0,
        max_retries=0,
    )
    ai_scored = 0
    batches = 0
    for offset in range(0, len(items), batch_size):
        batch = items[offset : offset + batch_size]
        batches += 1
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
                                _payload(batch),
                                ensure_ascii=False,
                                indent=2,
                            ),
                        },
                    ],
                    temperature=0.1,
                    stream=False,
                )
                content = response.choices[0].message.content or ""
                results = _extract_json_array(content)
                ai_scored += _apply_results(batch, results)
                completed = True
                break
            except Exception as exc:
                print(
                    f"警告：AI 评分第 {batches} 批第 {attempt} 次失败"
                    f"（{type(exc).__name__}）。"
                )
                if attempt < max_retries:
                    time.sleep(min(2 ** (attempt - 1), 4))
        if not completed:
            for item in batch:
                _fallback(
                    item,
                    "AI 批次评分失败，已使用规则评分。",
                )

    fallback = len(items) - ai_scored
    print(
        f"AI 新闻评分完成：总计 {len(items)} 条，"
        f"AI 成功 {ai_scored} 条，规则回退 {fallback} 条，"
        f"共 {batches} 批。"
    )
    return {
        "total": len(items),
        "ai_scored": ai_scored,
        "fallback": fallback,
        "batches": batches,
    }
