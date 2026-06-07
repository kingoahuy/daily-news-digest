import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

from src.models import NewsItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "news_digest.db"
DEFAULT_EMAIL_SETTINGS = {
    "email_enabled": "true",
    "email_send_time": "08:13",
    "timezone": "Asia/Singapore",
    "auto_send_local_enabled": "false",
}
DEFAULT_GENERATION_SETTINGS = {
    "low_api_mode": "true",
    "max_total_news": "12",
    "max_items_per_category": "3",
    "pre_ai_prefilter_limit": "40",
    "enable_bilingual_report": "false",
    "enable_enrichment": "true",
    "max_enriched_items": "1",
}


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def database_connection(
    db_path: Path = DEFAULT_DB_PATH,
) -> Iterator[sqlite3.Connection]:
    """打开数据库连接，并确保父目录与数据表存在。"""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        initialize_database(connection=connection)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_columns(
    connection: sqlite3.Connection,
    table_name: str,
    columns: Dict[str, str],
) -> None:
    existing = {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for name, definition in columns.items():
        if name not in existing:
            try:
                connection.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {name} {definition}"
                )
            except sqlite3.Error as exc:
                raise RuntimeError(
                    f"数据库升级失败：无法为 {table_name} 添加字段 {name}。"
                ) from exc
            print(f"数据库升级：{table_name} 新增字段 {name}。")


def initialize_database(
    db_path: Path = DEFAULT_DB_PATH,
    connection: Optional[sqlite3.Connection] = None,
) -> None:
    """初始化并增量升级数据库。重复调用不会删除历史数据。"""

    owns_connection = connection is None
    if connection is None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            core_topic TEXT,
            markdown_content TEXT NOT NULL,
            html_content TEXT NOT NULL,
            email_sent INTEGER NOT NULL DEFAULT 0,
            generated_at TEXT NOT NULL,
            report_path TEXT,
            radar_stats_json TEXT
        );

        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT NOT NULL,
            source TEXT,
            category TEXT,
            subcategory TEXT,
            published_at TEXT,
            score REAL NOT NULL DEFAULT 0,
            keywords TEXT,
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            ai_score REAL,
            ai_reason TEXT,
            ai_summary TEXT,
            ai_tags TEXT,
            importance_tier TEXT,
            cluster_id TEXT,
            cluster_title TEXT,
            enrichment_json TEXT,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            news_item_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN -2 AND 2),
            tags TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY (news_item_id) REFERENCES news_items(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preference_key TEXT NOT NULL,
            preference_value TEXT NOT NULL,
            weight REAL NOT NULL,
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (preference_key, preference_value, source)
        );

        CREATE TABLE IF NOT EXISTS news_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_item_id INTEGER NOT NULL,
            report_id INTEGER,
            action_type TEXT NOT NULL,
            action_value TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (news_item_id) REFERENCES news_items(id) ON DELETE CASCADE,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value TEXT,
            description TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS local_scheduler_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reports_date
            ON reports(report_date DESC);
        CREATE INDEX IF NOT EXISTS idx_news_report
            ON news_items(report_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_news_report_url
            ON news_items(report_id, url);
        CREATE INDEX IF NOT EXISTS idx_news_category
            ON news_items(category);
        CREATE INDEX IF NOT EXISTS idx_feedback_news
            ON feedback(news_item_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_news
            ON news_interactions(news_item_id, action_type);
        CREATE INDEX IF NOT EXISTS idx_interactions_report
            ON news_interactions(report_id, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_interactions_toggle
            ON news_interactions(news_item_id, action_type)
            WHERE action_type IN ('like', 'favorite');
        CREATE INDEX IF NOT EXISTS idx_scheduler_runs_date
            ON local_scheduler_runs(run_date, scheduled_time, status);
        """
    )

    _ensure_columns(
        connection,
        "reports",
        {
            "radar_stats_json": "TEXT",
        },
    )
    _ensure_columns(
        connection,
        "news_items",
        {
            "subcategory": "TEXT",
            "keywords": "TEXT",
            "is_active": "INTEGER NOT NULL DEFAULT 1",
            "ai_score": "REAL",
            "ai_reason": "TEXT",
            "ai_summary": "TEXT",
            "ai_tags": "TEXT",
            "importance_tier": "TEXT",
            "cluster_id": "TEXT",
            "cluster_title": "TEXT",
            "enrichment_json": "TEXT",
        },
    )
    _ensure_columns(
        connection,
        "news_interactions",
        {
            "report_id": "INTEGER",
            "action_value": "TEXT",
            "note": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        },
    )
    _ensure_columns(
        connection,
        "user_settings",
        {
            "description": "TEXT",
            "updated_at": "TEXT",
        },
    )
    _ensure_columns(
        connection,
        "local_scheduler_runs",
        {
            "message": "TEXT",
            "created_at": "TEXT",
        },
    )

    now = _utc_now_text()
    descriptions = {
        "email_enabled": "是否启用邮件推送",
        "email_send_time": "本地每日邮件发送时间",
        "timezone": "本地邮件调度时区",
        "auto_send_local_enabled": "是否启用本地自动发送",
        "low_api_mode": "是否启用省 API 模式",
        "max_total_news": "每期日报最多新闻数",
        "max_items_per_category": "每个分类最多新闻数",
        "pre_ai_prefilter_limit": "进入 AI 精评的候选新闻数",
        "enable_bilingual_report": "是否生成中英文双语日报",
        "enable_enrichment": "是否启用核心新闻背景补充",
        "max_enriched_items": "每期最多背景补充新闻数",
    }
    default_settings = {
        **DEFAULT_EMAIL_SETTINGS,
        **DEFAULT_GENERATION_SETTINGS,
    }
    connection.executemany(
        """
        INSERT OR IGNORE INTO user_settings (
            setting_key, setting_value, description, updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            (key, value, descriptions[key], now)
            for key, value in default_settings.items()
        ],
    )

    if owns_connection:
        connection.commit()
        connection.close()


def save_report(
    report_date: str,
    title: str,
    core_topic: str,
    markdown_content: str,
    html_content: str,
    email_sent: bool,
    report_path: str,
    radar_stats: Optional[Dict[str, object]] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """保存日报。同一天重复生成时更新原记录并返回其 ID。"""

    generated_at = _utc_now_text()
    with database_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO reports (
                report_date, title, core_topic, markdown_content,
                html_content, email_sent, generated_at, report_path,
                radar_stats_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_date) DO UPDATE SET
                title = excluded.title,
                core_topic = excluded.core_topic,
                markdown_content = excluded.markdown_content,
                html_content = excluded.html_content,
                email_sent = excluded.email_sent,
                generated_at = excluded.generated_at,
                report_path = excluded.report_path,
                radar_stats_json = excluded.radar_stats_json
            """,
            (
                report_date,
                title,
                core_topic,
                markdown_content,
                html_content,
                int(email_sent),
                generated_at,
                report_path,
                json.dumps(radar_stats or {}, ensure_ascii=False),
            ),
        )
        row = connection.execute(
            "SELECT id FROM reports WHERE report_date = ?",
            (report_date,),
        ).fetchone()
        return int(row["id"])


def save_news_items(
    report_id: int,
    items: Iterable[NewsItem],
    keyword_map: Optional[Dict[str, List[str]]] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """更新日报新闻，同时保留落选旧条目及其互动记录。"""

    item_list = list(items)
    keyword_map = keyword_map or {}
    created_at = _utc_now_text()
    with database_connection(db_path) as connection:
        connection.execute(
            "UPDATE news_items SET is_active = 0 WHERE report_id = ?",
            (report_id,),
        )
        connection.executemany(
            """
            INSERT INTO news_items (
                report_id, title, summary, url, source, category,
                subcategory, published_at, score, keywords, created_at,
                is_active, ai_score, ai_reason, ai_summary, ai_tags,
                importance_tier, cluster_id, cluster_title, enrichment_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id, url) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                source = excluded.source,
                category = excluded.category,
                subcategory = excluded.subcategory,
                published_at = excluded.published_at,
                score = excluded.score,
                keywords = excluded.keywords,
                created_at = excluded.created_at,
                is_active = 1,
                ai_score = excluded.ai_score,
                ai_reason = excluded.ai_reason,
                ai_summary = excluded.ai_summary,
                ai_tags = excluded.ai_tags,
                importance_tier = excluded.importance_tier,
                cluster_id = excluded.cluster_id,
                cluster_title = excluded.cluster_title,
                enrichment_json = excluded.enrichment_json
            """,
            [
                (
                    report_id,
                    item.title,
                    item.summary,
                    item.url,
                    item.source,
                    item.category,
                    item.subcategory,
                    item.published_at.isoformat() if item.published_at else None,
                    item.score,
                    json.dumps(
                        keyword_map.get(item.url, []),
                        ensure_ascii=False,
                    ),
                    created_at,
                    item.ai_score,
                    item.ai_reason,
                    item.ai_summary,
                    json.dumps(item.ai_tags, ensure_ascii=False),
                    item.importance_tier,
                    item.cluster_id,
                    item.cluster_title,
                    json.dumps(item.enrichment, ensure_ascii=False),
                )
                for item in item_list
            ],
        )
    return len(item_list)


def update_report_email_status(
    report_id: int,
    email_sent: bool,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    with database_connection(db_path) as connection:
        connection.execute(
            "UPDATE reports SET email_sent = ? WHERE id = ?",
            (int(email_sent), report_id),
        )


def get_latest_report(
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, object]]:
    with database_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM reports ORDER BY report_date DESC, id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_report(
    report_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, object]]:
    with database_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        return dict(row) if row else None


def list_reports(
    keyword: str = "",
    category: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    conditions = []
    parameters: List[object] = []

    if keyword.strip():
        conditions.append(
            "(r.title LIKE ? OR r.core_topic LIKE ? OR r.markdown_content LIKE ?)"
        )
        pattern = f"%{keyword.strip()}%"
        parameters.extend([pattern, pattern, pattern])
    if category.strip():
        conditions.append(
            "EXISTS (SELECT 1 FROM news_items n "
            "WHERE n.report_id = r.id AND n.category = ?)"
        )
        parameters.append(category.strip())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = (
        "SELECT r.* FROM reports r "
        f"{where_clause} ORDER BY r.report_date DESC, r.id DESC"
    )
    with database_connection(db_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]


def get_news_items(
    report_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM news_items
            WHERE report_id = ? AND is_active = 1
            ORDER BY score DESC, id ASC
            """,
            (report_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def save_feedback(
    report_id: int,
    news_item_id: int,
    rating: int,
    tags: Iterable[str],
    note: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    if rating < -2 or rating > 2:
        raise ValueError("rating 必须在 -2 到 2 之间。")

    tag_text = json.dumps(
        [tag.strip() for tag in tags if tag.strip()],
        ensure_ascii=False,
    )
    with database_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO feedback (
                report_id, news_item_id, rating, tags, note, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                news_item_id,
                rating,
                tag_text,
                note.strip(),
                _utc_now_text(),
            ),
        )
        return int(cursor.lastrowid)


def get_latest_feedback_for_news(
    news_item_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, object]]:
    with database_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT * FROM feedback
            WHERE news_item_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (news_item_id,),
        ).fetchone()
        return dict(row) if row else None


def list_feedback_with_news(
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                f.*, n.title, n.summary, n.category, n.subcategory,
                n.keywords, n.url, n.source
            FROM feedback f
            JOIN news_items n ON n.id = f.news_item_id
            ORDER BY f.id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def save_user_preference(
    preference_key: str,
    preference_value: str,
    weight: float,
    source: str = "manual",
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    with database_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO user_preferences (
                preference_key, preference_value, weight, source, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(preference_key, preference_value, source) DO UPDATE SET
                weight = excluded.weight,
                updated_at = excluded.updated_at
            """,
            (
                preference_key.strip(),
                preference_value.strip(),
                float(weight),
                source.strip(),
                _utc_now_text(),
            ),
        )


def list_user_preferences(
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM user_preferences
            ORDER BY preference_key, preference_value, source
            """
        ).fetchall()
        return [dict(row) for row in rows]


def _toggle_interaction(
    news_item_id: int,
    report_id: Optional[int],
    action_type: str,
    db_path: Path,
) -> bool:
    if action_type not in {"like", "favorite"}:
        raise ValueError("只允许切换 like 或 favorite。")

    with database_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT id FROM news_interactions
            WHERE news_item_id = ? AND action_type = ?
            LIMIT 1
            """,
            (news_item_id, action_type),
        ).fetchone()
        if row:
            connection.execute(
                "DELETE FROM news_interactions WHERE id = ?",
                (int(row["id"]),),
            )
            return False

        now = _utc_now_text()
        connection.execute(
            """
            INSERT INTO news_interactions (
                news_item_id, report_id, action_type, action_value,
                note, created_at, updated_at
            )
            VALUES (?, ?, ?, '1', '', ?, ?)
            """,
            (news_item_id, report_id, action_type, now, now),
        )
        return True


def toggle_like(
    news_item_id: int,
    report_id: Optional[int],
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """切换点赞状态，返回切换后的状态。"""

    return _toggle_interaction(news_item_id, report_id, "like", db_path)


def toggle_favorite(
    news_item_id: int,
    report_id: Optional[int],
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """切换收藏状态，返回切换后的状态。"""

    return _toggle_interaction(news_item_id, report_id, "favorite", db_path)


def add_comment(
    news_item_id: int,
    report_id: Optional[int],
    comment_text: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    text = comment_text.strip()
    if not text:
        raise ValueError("评论内容不能为空。")

    now = _utc_now_text()
    with database_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO news_interactions (
                news_item_id, report_id, action_type, action_value,
                note, created_at, updated_at
            )
            VALUES (?, ?, 'comment', ?, ?, ?, ?)
            """,
            (news_item_id, report_id, text, text, now, now),
        )
        return int(cursor.lastrowid)


def get_interaction_state(
    news_item_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT action_type, COUNT(*) AS count
            FROM news_interactions
            WHERE news_item_id = ?
            GROUP BY action_type
            """,
            (news_item_id,),
        ).fetchall()
    counts = {str(row["action_type"]): int(row["count"]) for row in rows}
    return {
        "liked": counts.get("like", 0) > 0,
        "favorited": counts.get("favorite", 0) > 0,
        "comment_count": counts.get("comment", 0),
    }


def get_news_comments(
    news_item_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM news_interactions
            WHERE news_item_id = ? AND action_type = 'comment'
            ORDER BY created_at DESC, id DESC
            """,
            (news_item_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_favorite_news(
    keyword: str = "",
    category: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    conditions = ["i.action_type = 'favorite'"]
    parameters: List[object] = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        conditions.append("(n.title LIKE ? OR n.summary LIKE ? OR n.keywords LIKE ?)")
        parameters.extend([pattern, pattern, pattern])
    if category.strip():
        conditions.append("n.category = ?")
        parameters.append(category.strip())

    with database_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT n.*, i.created_at AS favorited_at
            FROM news_interactions i
            JOIN news_items n ON n.id = i.news_item_id
            WHERE {' AND '.join(conditions)}
            ORDER BY i.created_at DESC, i.id DESC
            """,
            parameters,
        ).fetchall()
        return [dict(row) for row in rows]


def _interaction_news(
    action_type: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                i.*, n.title, n.summary, n.category, n.subcategory,
                n.keywords, n.url, n.source, n.published_at
            FROM news_interactions i
            JOIN news_items n ON n.id = i.news_item_id
            WHERE i.action_type = ?
            ORDER BY i.created_at DESC, i.id DESC
            """,
            (action_type,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_liked_news(
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    return _interaction_news("like", db_path)


def get_favorited_news(
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    return _interaction_news("favorite", db_path)


def get_commented_news(
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    return _interaction_news("comment", db_path)


def get_interaction_summary(
    report_id: Optional[int] = None,
    created_date: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, int]:
    conditions = []
    parameters: List[object] = []
    if report_id is not None:
        conditions.append("report_id = ?")
        parameters.append(report_id)
    if created_date:
        conditions.append("substr(created_at, 1, 10) = ?")
        parameters.append(created_date)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with database_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT action_type, COUNT(*) AS count
            FROM news_interactions
            {where_clause}
            GROUP BY action_type
            """,
            parameters,
        ).fetchall()
    counts = {str(row["action_type"]): int(row["count"]) for row in rows}
    return {
        "like": counts.get("like", 0),
        "favorite": counts.get("favorite", 0),
        "comment": counts.get("comment", 0),
        "total": sum(counts.values()),
    }


def get_interaction_based_preferences(
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, object]]:
    """返回带新闻元数据的全部互动，供偏好层做可解释汇总。"""

    with database_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                i.*, n.title, n.summary, n.category, n.subcategory,
                n.keywords, n.url, n.source
            FROM news_interactions i
            JOIN news_items n ON n.id = i.news_item_id
            ORDER BY i.created_at ASC, i.id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_setting(
    key: str,
    default: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[str]:
    with database_connection(db_path) as connection:
        row = connection.execute(
            "SELECT setting_value FROM user_settings WHERE setting_key = ?",
            (key,),
        ).fetchone()
        return str(row["setting_value"]) if row else default


def set_setting(
    key: str,
    value: object,
    description: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    with database_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO user_settings (
                setting_key, setting_value, description, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                description = CASE
                    WHEN excluded.description = '' THEN user_settings.description
                    ELSE excluded.description
                END,
                updated_at = excluded.updated_at
            """,
            (key.strip(), str(value), description.strip(), _utc_now_text()),
        )


def _as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_email_settings(
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    return {
        "email_enabled": _as_bool(
            get_setting("email_enabled", "true", db_path)
        ),
        "email_send_time": get_setting(
            "email_send_time", "08:13", db_path
        ),
        "timezone": get_setting(
            "timezone", "Asia/Singapore", db_path
        ),
        "auto_send_local_enabled": _as_bool(
            get_setting("auto_send_local_enabled", "false", db_path)
        ),
    }


def save_email_settings(
    email_enabled: bool,
    email_send_time: str,
    timezone_name: str,
    auto_send_local_enabled: bool,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    descriptions = {
        "email_enabled": "是否启用邮件推送",
        "email_send_time": "本地每日邮件发送时间",
        "timezone": "本地邮件调度时区",
        "auto_send_local_enabled": "是否启用本地自动发送",
    }
    values = {
        "email_enabled": str(bool(email_enabled)).lower(),
        "email_send_time": email_send_time,
        "timezone": timezone_name,
        "auto_send_local_enabled": str(bool(auto_send_local_enabled)).lower(),
    }
    for key, value in values.items():
        set_setting(key, value, descriptions[key], db_path)


def get_generation_settings(
    defaults: Optional[Dict[str, object]] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    configured = defaults or {}

    def default_text(key: str) -> str:
        value = configured.get(key, DEFAULT_GENERATION_SETTINGS[key])
        return str(value).lower() if isinstance(value, bool) else str(value)

    return {
        "low_api_mode": _as_bool(
            get_setting("low_api_mode", default_text("low_api_mode"), db_path)
        ),
        "max_total_news": int(
            get_setting(
                "max_total_news",
                default_text("max_total_news"),
                db_path,
            )
        ),
        "max_items_per_category": int(
            get_setting(
                "max_items_per_category",
                default_text("max_items_per_category"),
                db_path,
            )
        ),
        "pre_ai_prefilter_limit": int(
            get_setting(
                "pre_ai_prefilter_limit",
                default_text("pre_ai_prefilter_limit"),
                db_path,
            )
        ),
        "enable_bilingual_report": _as_bool(
            get_setting(
                "enable_bilingual_report",
                default_text("enable_bilingual_report"),
                db_path,
            )
        ),
        "enable_enrichment": _as_bool(
            get_setting(
                "enable_enrichment",
                default_text("enable_enrichment"),
                db_path,
            )
        ),
        "max_enriched_items": int(
            get_setting(
                "max_enriched_items",
                default_text("max_enriched_items"),
                db_path,
            )
        ),
    }


def save_generation_settings(
    low_api_mode: bool,
    max_total_news: int,
    max_items_per_category: int,
    pre_ai_prefilter_limit: int,
    enable_bilingual_report: bool,
    enable_enrichment: bool,
    max_enriched_items: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    descriptions = {
        "low_api_mode": "是否启用省 API 模式",
        "max_total_news": "每期日报最多新闻数",
        "max_items_per_category": "每个分类最多新闻数",
        "pre_ai_prefilter_limit": "进入 AI 精评的候选新闻数",
        "enable_bilingual_report": "是否生成中英文双语日报",
        "enable_enrichment": "是否启用核心新闻背景补充",
        "max_enriched_items": "每期最多背景补充新闻数",
    }
    values = {
        "low_api_mode": str(bool(low_api_mode)).lower(),
        "max_total_news": str(max(1, int(max_total_news))),
        "max_items_per_category": str(
            max(1, int(max_items_per_category))
        ),
        "pre_ai_prefilter_limit": str(
            max(1, int(pre_ai_prefilter_limit))
        ),
        "enable_bilingual_report": str(
            bool(enable_bilingual_report)
        ).lower(),
        "enable_enrichment": str(bool(enable_enrichment)).lower(),
        "max_enriched_items": str(max(1, int(max_enriched_items))),
    }
    for key, value in values.items():
        set_setting(key, value, descriptions[key], db_path)


def scheduler_has_success(
    run_date: str,
    scheduled_time: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    with database_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT 1 FROM local_scheduler_runs
            WHERE run_date = ? AND scheduled_time = ? AND status = 'success'
            LIMIT 1
            """,
            (run_date, scheduled_time),
        ).fetchone()
        return row is not None


def record_scheduler_run(
    run_date: str,
    scheduled_time: str,
    status: str,
    message: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    if status not in {"success", "failed", "skipped"}:
        raise ValueError("调度状态必须是 success、failed 或 skipped。")
    with database_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO local_scheduler_runs (
                run_date, scheduled_time, status, message, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_date,
                scheduled_time,
                status,
                message[:1000],
                _utc_now_text(),
            ),
        )
        return int(cursor.lastrowid)


def get_latest_scheduler_run(
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, object]]:
    with database_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT * FROM local_scheduler_runs
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None
