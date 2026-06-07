import json
from collections import Counter
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from src.config import load_settings
from src.database import (
    add_comment,
    get_favorite_news,
    get_interaction_state,
    get_interaction_summary,
    get_latest_report,
    get_news_comments,
    get_news_item,
    get_news_items,
    get_user_settings,
    initialize_database,
    list_reports,
    save_user_settings,
    toggle_favorite,
    toggle_like,
)
from src.preference import build_user_preference_profile


settings = load_settings(send_email=False, require_api_key=False)
DB_PATH = settings.database_path
PREFERENCES_PATH = settings.preferences_path


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(DB_PATH)
    yield


app = FastAPI(
    title="Daily News Digest API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):30\d{2}$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("评论内容不能为空")
        return content


class UserSettingsUpdate(BaseModel):
    email_enabled: bool
    email_send_time: str
    low_api_mode: bool
    max_total_news: int = Field(ge=1, le=100)
    max_items_per_category: int = Field(ge=1, le=30)
    enable_bilingual_report: bool
    enable_enrichment: bool

    @field_validator("email_send_time")
    @classmethod
    def validate_send_time(cls, value: str) -> str:
        time_text = value.strip()
        parts = time_text.split(":")
        if (
            len(parts) != 2
            or any(len(part) != 2 or not part.isdigit() for part in parts)
            or not 0 <= int(parts[0]) <= 23
            or not 0 <= int(parts[1]) <= 59
        ):
            raise ValueError("推送时间必须使用 HH:MM 格式")
        return time_text

    @model_validator(mode="after")
    def validate_news_limits(self):
        if self.max_items_per_category > self.max_total_news:
            raise ValueError("每类新闻数量不能大于新闻总数")
        return self


def _json_list(value: object) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return [part.strip() for part in str(value).split(",") if part.strip()]
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _json_dict(value: object) -> Dict[str, object]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _report_payload(report: Dict[str, object]) -> Dict[str, object]:
    return {
        "report_id": int(report["id"]),
        "report_date": str(report["report_date"]),
        "title": str(report["title"]),
        "core_topic": str(report.get("core_topic") or ""),
        "markdown_content": str(report.get("markdown_content") or ""),
        "generated_at": str(report.get("generated_at") or ""),
        "email_sent": bool(report.get("email_sent")),
    }


def _news_payload(
    news: Dict[str, object],
    include_interactions: bool = True,
) -> Dict[str, object]:
    payload = {
        "id": int(news["id"]),
        "report_id": int(news["report_id"]),
        "title": str(news.get("title") or ""),
        "summary": str(news.get("summary") or ""),
        "url": str(news.get("url") or ""),
        "source": str(news.get("source") or ""),
        "category": str(news.get("category") or "society"),
        "published_at": str(news.get("published_at") or ""),
        "score": float(news.get("score") or 0),
        "ai_score": float(news.get("ai_score") or 0),
        "ai_reason": str(news.get("ai_reason") or ""),
        "ai_summary": str(news.get("ai_summary") or ""),
        "ai_tags": _json_list(news.get("ai_tags")),
        "importance_tier": str(news.get("importance_tier") or ""),
        "cluster_title": str(news.get("cluster_title") or ""),
        "enrichment": _json_dict(news.get("enrichment_json")),
    }
    if news.get("favorited_at"):
        payload["favorited_at"] = str(news["favorited_at"])
    if include_interactions:
        payload["interactions"] = get_interaction_state(
            int(news["id"]),
            DB_PATH,
        )
    return payload


def _require_news(news_id: int) -> Dict[str, object]:
    news = get_news_item(news_id, DB_PATH)
    if not news:
        raise HTTPException(status_code=404, detail="新闻不存在。")
    return news


@app.get("/api/health")
def health() -> Dict[str, object]:
    latest = get_latest_report(DB_PATH)
    return {
        "status": "ok",
        "database": str(DB_PATH),
        "has_report": latest is not None,
    }


@app.get("/api/reports/latest")
def latest_report() -> Dict[str, object]:
    report = get_latest_report(DB_PATH)
    if not report:
        raise HTTPException(status_code=404, detail="还没有生成日报。")
    return _report_payload(report)


@app.get("/api/reports/{report_id}/news")
def report_news(report_id: int) -> List[Dict[str, object]]:
    rows = get_news_items(report_id, DB_PATH)
    return [_news_payload(row) for row in rows]


@app.get("/api/news/{news_id}")
def news_detail(news_id: int) -> Dict[str, object]:
    return _news_payload(_require_news(news_id))


@app.get("/api/news/{news_id}/interactions")
def interactions(news_id: int) -> Dict[str, object]:
    _require_news(news_id)
    return get_interaction_state(news_id, DB_PATH)


@app.post("/api/news/{news_id}/like")
def like(news_id: int) -> Dict[str, object]:
    news = _require_news(news_id)
    active = toggle_like(news_id, int(news["report_id"]), DB_PATH)
    return {
        "active": active,
        "interactions": get_interaction_state(news_id, DB_PATH),
    }


@app.post("/api/news/{news_id}/favorite")
def favorite(news_id: int) -> Dict[str, object]:
    news = _require_news(news_id)
    active = toggle_favorite(news_id, int(news["report_id"]), DB_PATH)
    return {
        "active": active,
        "interactions": get_interaction_state(news_id, DB_PATH),
    }


@app.post("/api/news/{news_id}/comments")
def create_comment(
    news_id: int,
    body: CommentCreate,
) -> Dict[str, object]:
    news = _require_news(news_id)
    comment_id = add_comment(
        news_id,
        int(news["report_id"]),
        body.content,
        DB_PATH,
    )
    return {
        "id": comment_id,
        "interactions": get_interaction_state(news_id, DB_PATH),
    }


@app.get("/api/news/{news_id}/comments")
def comments(news_id: int) -> List[Dict[str, object]]:
    _require_news(news_id)
    return [
        {
            "id": int(row["id"]),
            "content": str(row.get("action_value") or row.get("note") or ""),
            "created_at": str(row.get("created_at") or ""),
        }
        for row in get_news_comments(news_id, DB_PATH)
    ]


@app.get("/api/favorites")
def favorites() -> List[Dict[str, object]]:
    return [_news_payload(row) for row in get_favorite_news(db_path=DB_PATH)]


@app.get("/api/profile")
def profile() -> Dict[str, object]:
    profile_data = build_user_preference_profile(
        PREFERENCES_PATH,
        DB_PATH,
    )
    return {
        **profile_data,
        "interaction_summary": get_interaction_summary(db_path=DB_PATH),
    }


@app.get("/api/settings")
def user_settings() -> Dict[str, object]:
    return get_user_settings(settings.filtering, DB_PATH)


@app.put("/api/settings")
def update_user_settings(
    body: UserSettingsUpdate,
) -> Dict[str, object]:
    try:
        return save_user_settings(
            email_enabled=body.email_enabled,
            email_send_time=body.email_send_time,
            low_api_mode=body.low_api_mode,
            max_total_news=body.max_total_news,
            max_items_per_category=body.max_items_per_category,
            enable_bilingual_report=body.enable_bilingual_report,
            enable_enrichment=body.enable_enrichment,
            db_path=DB_PATH,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/analytics")
def analytics() -> Dict[str, object]:
    reports = list_reports(db_path=DB_PATH)[:7]
    latest = reports[0] if reports else None
    latest_items = get_news_items(int(latest["id"]), DB_PATH) if latest else []
    category_counts = Counter(
        str(item.get("category") or "society") for item in latest_items
    )
    source_counts = Counter(
        str(item.get("source") or "未知来源") for item in latest_items
    )
    trend = []
    for report in reversed(reports):
        items = get_news_items(int(report["id"]), DB_PATH)
        scores = [
            float(item.get("ai_score") or item.get("score") or 0)
            for item in items
        ]
        trend.append(
            {
                "date": str(report["report_date"])[5:],
                "important_count": sum(score >= 7.5 for score in scores),
                "average_score": (
                    round(sum(scores) / len(scores), 2) if scores else 0
                ),
            }
        )
    return {
        "report_count": len(reports),
        "latest_news_count": len(latest_items),
        "category_counts": dict(category_counts),
        "source_counts": dict(source_counts),
        "trend": trend,
        "interaction_summary": get_interaction_summary(db_path=DB_PATH),
    }
