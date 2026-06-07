from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import streamlit as st

from src.config import ConfigError, load_settings
from src.database import (
    add_comment,
    get_email_settings,
    get_favorite_news,
    get_generation_settings,
    get_interaction_state,
    get_interaction_summary,
    get_latest_report,
    get_latest_scheduler_run,
    get_news_comments,
    get_news_items,
    initialize_database,
    list_reports,
    save_email_settings,
    save_generation_settings,
    toggle_favorite,
    toggle_like,
)
from src.preference import build_user_preference_profile
from src.ui_styles import (
    clamp_text,
    clamp_title,
    inject_shadcn_styles,
    render_badge_html,
    render_card_header_html,
    render_empty_state_html,
    render_metric_card_html,
)
from src.web_utils import (
    CATEGORY_LABELS,
    display_time,
    email_configuration_complete,
    next_email_time_text,
    parse_json_dict,
    parse_json_list,
    parse_send_time,
    run_digest_command,
)


PROJECT_ROOT = Path(__file__).resolve().parent
PAGE_HOME = "home"
PAGE_RADAR = "radar"
PAGE_TODAY = "today"
PAGE_HISTORY = "history"
PAGE_INTERACTIONS = "interactions"
PAGE_FAVORITES = "favorites"
PAGE_PROFILE = "profile"
PAGE_EMAIL = "email"
PAGE_GENERATE = "generate"

PAGE_TITLES = {
    PAGE_RADAR: "AI 新闻雷达",
    PAGE_TODAY: "今日日报",
    PAGE_HISTORY: "历史日报",
    PAGE_INTERACTIONS: "新闻互动",
    PAGE_FAVORITES: "我的收藏",
    PAGE_PROFILE: "我的偏好画像",
    PAGE_EMAIL: "设置",
    PAGE_GENERATE: "手动生成日报",
}

st.set_page_config(
    page_title="个人 AI 新闻雷达",
    page_icon="📰",
    layout="wide",
)


def inject_styles() -> None:
    inject_shadcn_styles()


@st.cache_resource
def app_settings():
    return load_settings(send_email=False, require_api_key=False)


def go_to(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()


def render_metric_card(
    icon: str,
    label: str,
    value: object,
    note: str = "",
) -> None:
    st.markdown(
        render_metric_card_html(icon, label, value, note),
        unsafe_allow_html=True,
    )


def page_header(title: str, description: str = "") -> None:
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title(title)
        if description:
            st.markdown(
                f'<p class="page-description">{escape(description)}</p>',
                unsafe_allow_html=True,
            )
    with col2:
        if st.button(
            "← 返回首页",
            key=f"back_{st.session_state['page']}",
            type="tertiary",
        ):
            go_to(PAGE_HOME)


def report_download(report, key_suffix: str) -> None:
    st.download_button(
        "下载 Markdown",
        data=str(report["markdown_content"]),
        file_name=f"daily_news_{report['report_date']}.md",
        mime="text/markdown",
        key=f"download_{key_suffix}",
    )


def render_report_summary(report) -> None:
    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        render_metric_card(
            "▤",
            "日报日期",
            str(report["report_date"]),
            "当前报告版本",
        )
    with col2:
        render_metric_card(
            "◷",
            "生成时间",
            display_time(report["generated_at"]),
            "本地记录时间",
        )
    with col3:
        render_metric_card(
            "✓" if int(report["email_sent"]) else "·",
            "邮件状态",
            "已发送" if int(report["email_sent"]) else "未发送",
            "本期投递状态",
        )
    st.markdown(
        '<div class="shad-alert"><div class="shad-alert-icon">◎</div>'
        '<div><div class="shad-alert-title">核心议题</div>'
        f'<div class="shad-alert-description">'
        f'{escape(str(report["core_topic"] or "未记录"))}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def render_news_card(
    news_item,
    report_id: int,
    db_path: Path,
    key_prefix: str,
    show_interactions: bool = True,
) -> None:
    news_id = int(news_item["id"])
    unique_key = f"{key_prefix}_{news_id}"
    keywords = parse_json_list(news_item.get("keywords"))
    ai_tags = parse_json_list(news_item.get("ai_tags"))
    enrichment = parse_json_dict(news_item.get("enrichment_json"))
    category = CATEGORY_LABELS.get(
        str(news_item.get("category") or ""),
        str(news_item.get("category") or "未分类"),
    )
    state = (
        get_interaction_state(news_id, db_path)
        if show_interactions
        else {
            "liked": False,
            "favorited": False,
            "comment_count": 0,
        }
    )
    tier = str(news_item.get("importance_tier") or "未标注")
    tier_variant = {
        "high": "primary",
        "medium": "secondary",
        "low": "outline",
        "noise": "muted",
    }.get(tier, "outline")
    score = float(
        news_item.get("ai_score") or news_item.get("score") or 0
    )
    header_badges = [
        render_badge_html(category, "secondary"),
        render_badge_html(f"AI {score:.1f}", "primary"),
        render_badge_html(tier, tier_variant),
    ]
    if show_interactions and state["liked"]:
        header_badges.append(render_badge_html("已点赞", "success"))
    if show_interactions and state["favorited"]:
        header_badges.append(render_badge_html("已收藏", "warning"))

    with st.container(border=True):
        full_title = str(news_item["title"])
        display_title = clamp_title(full_title)
        st.markdown(
            '<div class="shad-card-header news-card-header">'
            f'<div class="shad-badge-wrap">{"".join(header_badges)}</div>'
            '<div class="news-title" '
            f'title="{escape(full_title, quote=True)}">'
            f"{escape(display_title)}</div>"
            '<div class="news-meta">'
            f'{escape(str(news_item.get("source") or "未知来源"))} · '
            f'{escape(display_time(news_item.get("published_at")))}'
            "</div></div>",
            unsafe_allow_html=True,
        )
        summary = clamp_text(
            news_item.get("summary") or "RSS 未提供摘要。",
            200,
        )
        st.markdown(
            '<div class="shad-card-content">'
            f'<div class="news-summary">{escape(summary)}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        tags = (ai_tags or keywords)[:6]
        hidden_tag_count = max(len(ai_tags or keywords) - len(tags), 0)
        if tags:
            tag_html = "".join(
                render_badge_html(word, "muted")
                for word in tags
            )
            if hidden_tag_count:
                tag_html += render_badge_html(
                    f"+{hidden_tag_count}",
                    "outline",
                )
            st.markdown(
                f'<div class="shad-badge-wrap">{tag_html}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<a class="news-source-link" '
            f'href="{escape(str(news_item["url"]), quote=True)}" '
            'target="_blank" rel="noopener noreferrer">查看原文 ↗</a>',
            unsafe_allow_html=True,
        )

        ai_summary = str(news_item.get("ai_summary") or "").strip()
        ai_reason = str(news_item.get("ai_reason") or "").strip()
        has_analysis = bool(
            ai_summary
            or ai_reason
            or news_item.get("cluster_title")
            or enrichment
            or state["comment_count"]
        )
        if show_interactions:
            st.markdown(
                '<div class="shad-card-footer">'
                '<span class="shad-muted">新闻互动</span></div>',
                unsafe_allow_html=True,
            )
            like_label = "👍 取消点赞" if state["liked"] else "👍 点赞"
            favorite_label = (
                "⭐ 取消收藏" if state["favorited"] else "⭐ 收藏"
            )
            col1, col2, col3 = st.columns([1, 1, 2])
            if col1.button(like_label, key=f"like_{unique_key}"):
                active = toggle_like(news_id, report_id, db_path)
                st.toast("已点赞" if active else "已取消点赞")
                st.rerun()
            if col2.button(
                favorite_label,
                key=f"favorite_{unique_key}",
            ):
                active = toggle_favorite(news_id, report_id, db_path)
                st.toast("已收藏" if active else "已取消收藏")
                st.rerun()
            if col3.button(
                f"💬 评论（{state['comment_count']}）",
                key=f"comment_toggle_{unique_key}",
            ):
                session_key = f"comment_open_{unique_key}"
                st.session_state[session_key] = not st.session_state.get(
                    session_key, False
                )

            if st.session_state.get(
                f"comment_open_{unique_key}",
                False,
            ):
                comment = st.text_area(
                    "写下你的想法",
                    key=f"comment_text_{unique_key}",
                    placeholder="例如：重要，继续关注这个主题。",
                )
                if st.button(
                    "保存评论",
                    key=f"comment_save_{unique_key}",
                    type="primary",
                ):
                    if not comment.strip():
                        st.warning("评论内容为空，未保存。")
                    else:
                        add_comment(
                            news_id,
                            report_id,
                            comment,
                            db_path,
                        )
                        st.session_state[
                            f"comment_open_{unique_key}"
                        ] = False
                        st.toast("评论已保存")
                        st.rerun()

        if has_analysis:
            with st.expander("AI 分析与背景", expanded=False):
                st.caption(
                    "综合排序分 "
                    f"{float(news_item.get('score') or 0):.2f} · "
                    f"重要性 {str(news_item.get('importance_tier') or '未标注')}"
                )
                if ai_reason:
                    st.markdown("**AI 推荐理由**")
                    st.markdown(
                        f'<div class="ai-reason">'
                        f'{escape(ai_reason).replace(chr(10), "<br>")}'
                        "</div>",
                        unsafe_allow_html=True,
                    )
                if ai_summary and ai_summary != str(
                    news_item.get("summary") or ""
                ):
                    st.markdown("**AI 摘要**")
                    st.write(ai_summary)
                if news_item.get("cluster_title"):
                    st.markdown(
                        '<div class="cluster-line">'
                        "主题簇："
                        f'{escape(str(news_item["cluster_title"]))}'
                        "</div>",
                        unsafe_allow_html=True,
                    )
                for key, label in (
                    ("whats_new", "最新变化"),
                    ("why_it_matters", "为何重要"),
                    ("background", "背景"),
                    ("possible_impact", "可能影响"),
                ):
                    value = str(enrichment.get(key) or "").strip()
                    if value:
                        st.markdown(f"**{label}**")
                        st.write(value)
                points = enrichment.get("follow_up_points") or []
                if points:
                    st.markdown("**后续看点**")
                    for point in points:
                        st.markdown(f"- {point}")
                if show_interactions and state["comment_count"]:
                    comments = get_news_comments(news_id, db_path)
                    if comments:
                        st.markdown("**已有评论**")
                        for row in comments:
                            st.markdown(
                                f"- {row['action_value']}  "
                                f"`{display_time(row['created_at'])}`"
                            )

def render_home(settings) -> None:
    latest = get_latest_report(settings.database_path)
    email_settings = get_email_settings(settings.database_path)
    today = datetime.now(ZoneInfo(settings.timezone)).date().isoformat()
    is_today = bool(latest and latest["report_date"] == today)
    today_items = (
        get_news_items(int(latest["id"]), settings.database_path)
        if is_today
        else []
    )
    interactions = get_interaction_summary(db_path=settings.database_path)
    email_active = bool(
        email_settings["email_enabled"]
        and email_settings["auto_send_local_enabled"]
    )
    next_email = next_email_time_text(
        email_settings["email_send_time"],
        str(email_settings["timezone"]),
        email_active,
    )
    hero_badges = [
        render_badge_html(
            "今日已生成" if is_today else "今日未生成",
            "success" if is_today else "outline",
        ),
        render_badge_html(
            "邮件调度开启" if email_active else "邮件调度关闭",
            "secondary" if email_active else "muted",
        ),
    ]
    st.markdown(
        '<div class="shad-card shad-hero">'
        "<div>"
        '<div class="shad-hero-title">个人 AI 新闻雷达</div>'
        '<p class="shad-hero-description">'
        "更少、更重要、更符合你偏好的每日新闻简报。"
        "</p></div>"
        '<div class="shad-hero-meta">'
        f'<div class="shad-meta-line">{escape(today)}</div>'
        f'<div class="shad-meta-line">下次邮件：{escape(next_email)}</div>'
        f'<div class="shad-badge-wrap">{"".join(hero_badges)}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4, gap="small")
    report_status = "已生成" if is_today else "未生成"
    report_note = "等待今日简报"
    if is_today:
        report_note = (
            "邮件已发送" if int(latest["email_sent"]) else "邮件未发送"
        )
    with col1:
        render_metric_card("◉", "今日日报", report_status, report_note)
    with col2:
        render_metric_card("▤", "今日新闻", len(today_items), "精选主题")
    with col3:
        render_metric_card(
            "♡",
            "互动记录",
            interactions["total"],
            f"赞 {interactions['like']} · 藏 {interactions['favorite']} · 评 {interactions['comment']}",
        )
    with col4:
        render_metric_card(
            "◷",
            "下次邮件",
            next_email,
            "本地调度时间",
        )

    st.markdown(
        '<div class="shad-section-heading">'
        '<div><div class="shad-section-title">功能导航</div>'
        '<div class="shad-section-description">查看日报、雷达与个人设置</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )
    cards = [
        (PAGE_TODAY, "▤", "今日", "查看最新简报"),
        (PAGE_RADAR, "◎", "雷达", "查看 AI 评分与聚类"),
        (PAGE_INTERACTIONS, "♡", "互动", "点赞、收藏、评论"),
        (PAGE_FAVORITES, "☆", "收藏", "查看重点新闻"),
        (PAGE_HISTORY, "◷", "历史", "回看往期日报"),
        (PAGE_PROFILE, "◌", "画像", "了解你的关注偏好"),
        (PAGE_EMAIL, "⚙", "设置", "邮件与生成配置"),
        (PAGE_GENERATE, "↻", "生成", "手动刷新日报"),
    ]
    for start in range(0, len(cards), 4):
        columns = st.columns(4, gap="small")
        for column, card in zip(columns, cards[start : start + 4]):
            page, icon, title, description = card
            with column:
                with st.container(border=True):
                    st.markdown(
                        '<div class="shad-nav-card">'
                        + render_card_header_html(
                            title,
                            description,
                            icon,
                        )
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"进入{title}",
                        key=f"home_nav_{page}",
                        width="stretch",
                    ):
                        go_to(page)


def page_radar(settings) -> None:
    page_header(
        "AI 新闻雷达",
        "查看评分、主题聚类、阈值过滤和个性化排序影响。",
    )
    report = get_latest_report(settings.database_path)
    if not report:
        st.info("数据库中还没有日报。请先手动生成。")
        return
    items = get_news_items(int(report["id"]), settings.database_path)
    stats = parse_json_dict(report.get("radar_stats_json"))
    high_items = [
        item
        for item in items
        if float(item.get("ai_score") or 0) >= 8
    ]
    clusters = list(stats.get("clusters") or [])
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        render_metric_card("↑", "高分新闻", len(high_items), "AI 分数 8+")
    with c2:
        render_metric_card(
            "⌁",
            "低分过滤",
            int(stats.get("filtered_count", 0)),
            "未进入日报",
        )
    with c3:
        render_metric_card(
            "◎",
            "主题聚类",
            int(stats.get("cluster_count", 0)),
            "去重后的事件簇",
        )
    with c4:
        render_metric_card(
            "◇",
            "多来源主题",
            int(stats.get("multi_source_cluster_count", 0)),
            "多个来源共同报道",
        )

    category_averages = dict(stats.get("category_averages") or {})
    if category_averages:
        category_frame = pd.DataFrame(
            [
                {
                    "分类": CATEGORY_LABELS.get(category, category),
                    "平均 AI 分": float(score),
                }
                for category, score in category_averages.items()
            ]
        ).set_index("分类")
        with st.container(border=True):
            st.markdown(
                render_card_header_html(
                    "分类平均分",
                    "比较各新闻分类的平均 AI 重要性评分。",
                ),
                unsafe_allow_html=True,
            )
            st.bar_chart(category_frame)
            st.dataframe(category_frame, width="stretch")

    impact = dict(stats.get("preference_impact") or {})
    with st.container(border=True):
        st.markdown(
            render_card_header_html(
                "偏好影响",
                "点赞、收藏与评论如何影响本期排序。",
            ),
            unsafe_allow_html=True,
        )
        p1, p2, p3 = st.columns(3, gap="small")
        with p1:
            render_metric_card(
                "±",
                "平均调整",
                f"{float(impact.get('average_adjustment', 0)):+.3f}",
                "个性化分数变化",
            )
        with p2:
            render_metric_card(
                "+",
                "获得加分",
                int(impact.get("boosted_items", 0)),
                "符合当前偏好",
            )
        with p3:
            render_metric_card(
                "−",
                "被降低",
                int(impact.get("reduced_items", 0)),
                "与偏好相关性较低",
            )

    if clusters:
        cluster_frame = pd.DataFrame(
            [
                {
                    "主题": row.get("main_title", ""),
                    "来源数": len(row.get("sources") or []),
                    "关联新闻": int(row.get("related_count", 0)),
                    "聚类分": float(row.get("cluster_score", 0)),
                    "来源": " / ".join(row.get("sources") or []),
                }
                for row in clusters[:60]
            ]
        )
        with st.container(border=True):
            st.markdown(
                render_card_header_html(
                    "主题聚类结果",
                    f"展示前 {len(cluster_frame)} 个主题簇，保留来源信息。",
                ),
                unsafe_allow_html=True,
            )
            st.dataframe(
                cluster_frame,
                width="stretch",
                hide_index=True,
            )

    st.markdown(
        '<div class="shad-section-heading">'
        '<div><div class="shad-section-title">今日高分新闻</div>'
        '<div class="shad-section-description">按 AI 分数从高到低展示</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )
    visible = sorted(
        items,
        key=lambda item: float(item.get("ai_score") or 0),
        reverse=True,
    )[:10]
    if not visible:
        st.markdown(
            render_empty_state_html(
                "暂无高分新闻",
                "本期没有达到展示条件的新闻。",
                "◎",
            ),
            unsafe_allow_html=True,
        )
        return
    for item in visible:
        render_news_card(
            item,
            int(report["id"]),
            settings.database_path,
            key_prefix=f"radar_{report['id']}",
        )


def page_today(settings) -> None:
    page_header("今日日报", "阅读最新简报，并从新闻互动页留下反馈。")
    report = get_latest_report(settings.database_path)
    if not report:
        st.info("数据库中还没有日报。请先手动生成今日日报。")
        return
    render_report_summary(report)
    report_download(report, "today")
    with st.container(border=True):
        st.markdown(str(report["markdown_content"]))


def page_history(settings) -> None:
    page_header("历史日报", "按关键词或分类回看过去的新闻简报。")
    col1, col2 = st.columns(2)
    keyword = col1.text_input("关键词搜索", key="history_keyword")
    category_options = ["全部"] + list(CATEGORY_LABELS.values())
    category_label = col2.selectbox(
        "按分类筛选", category_options, key="history_category"
    )
    category = next(
        (
            key
            for key, label in CATEGORY_LABELS.items()
            if label == category_label
        ),
        "",
    )
    reports = list_reports(keyword, category, settings.database_path)
    if not reports:
        st.info("没有找到符合条件的历史日报。")
        return
    report_map = {
        f"{row['report_date']}｜{row['core_topic']}": row for row in reports
    }
    label = st.selectbox("选择日报", list(report_map), key="history_report")
    report = report_map[label]
    render_report_summary(report)
    report_download(report, str(report["id"]))
    with st.container(border=True):
        st.markdown(str(report["markdown_content"]))


def page_interactions(settings) -> None:
    page_header(
        "新闻互动",
        "对新闻点赞、收藏或评论，下一次排序会参考这些记录。",
    )
    reports = list_reports(db_path=settings.database_path)
    if not reports:
        st.info("暂无日报，请先生成今日日报。")
        return
    report_map = {
        f"{row['report_date']}｜{row['core_topic']}": row for row in reports
    }
    selected_label = st.selectbox(
        "选择日报", list(report_map), key="interaction_report"
    )
    report = report_map[selected_label]
    items = get_news_items(int(report["id"]), settings.database_path)
    summary = get_interaction_summary(
        report_id=int(report["id"]),
        db_path=settings.database_path,
    )
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        render_metric_card("♡", "点赞", summary["like"], "当前日报")
    with c2:
        render_metric_card("☆", "收藏", summary["favorite"], "当前日报")
    with c3:
        render_metric_card("◌", "评论", summary["comment"], "当前日报")

    f1, f2, f3 = st.columns(3)
    category_label = f1.selectbox(
        "分类",
        ["全部"] + list(CATEGORY_LABELS.values()),
        key="interaction_category",
    )
    only_unseen = f2.toggle("只看未互动新闻", key="only_unseen")
    only_favorites = f3.toggle("只看已收藏新闻", key="only_favorites")
    category = next(
        (
            key
            for key, label in CATEGORY_LABELS.items()
            if label == category_label
        ),
        "",
    )

    visible_items = []
    for item in items:
        if category and item["category"] != category:
            continue
        state = get_interaction_state(int(item["id"]), settings.database_path)
        if only_unseen and (
            state["liked"] or state["favorited"] or state["comment_count"]
        ):
            continue
        if only_favorites and not state["favorited"]:
            continue
        visible_items.append(item)

    st.caption(f"当前显示 {len(visible_items)} 条新闻")
    for item in visible_items:
        render_news_card(
            item,
            int(report["id"]),
            settings.database_path,
            key_prefix=f"interaction_{report['id']}",
        )


def page_favorites(settings) -> None:
    page_header("我的收藏", "按收藏时间倒序查看重要新闻。")
    col1, col2 = st.columns(2)
    keyword = col1.text_input("搜索收藏", key="favorite_keyword")
    category_label = col2.selectbox(
        "分类",
        ["全部"] + list(CATEGORY_LABELS.values()),
        key="favorite_category",
    )
    category = next(
        (
            key
            for key, label in CATEGORY_LABELS.items()
            if label == category_label
        ),
        "",
    )
    favorites = get_favorite_news(
        keyword,
        category,
        settings.database_path,
    )
    if not favorites:
        st.info("还没有收藏新闻。可以在“新闻互动”页面点击 ⭐ 收藏。")
        return
    for item in favorites:
        st.caption(f"收藏时间：{display_time(item['favorited_at'])}")
        render_news_card(
            item,
            int(item["report_id"]),
            settings.database_path,
            key_prefix="favorites",
        )


def _top_category(counts) -> str:
    if not counts:
        return "暂无"
    category = max(counts, key=counts.get)
    return CATEGORY_LABELS.get(category, category)


def page_profile(settings) -> None:
    page_header(
        "我的偏好画像",
        "画像来自初始偏好、历史评分以及点赞、收藏和评论。",
    )
    profile = build_user_preference_profile(
        settings.preferences_path,
        settings.database_path,
    )
    action_counts = dict(profile.get("action_category_counts") or {})
    like_counts = dict(action_counts.get("like") or {})
    favorite_counts = dict(action_counts.get("favorite") or {})
    comment_counts = dict(action_counts.get("comment") or {})

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        render_metric_card(
            "♡",
            "最常点赞分类",
            _top_category(like_counts),
            "来自点赞记录",
        )
    with c2:
        render_metric_card(
            "☆",
            "最常收藏分类",
            _top_category(favorite_counts),
            "来自收藏记录",
        )
    with c3:
        render_metric_card(
            "◌",
            "评论最多分类",
            _top_category(comment_counts),
            "来自评论记录",
        )

    category_weights = dict(profile.get("category_weights") or {})
    interaction_adjustments = dict(
        profile.get("interaction_category_adjustments") or {}
    )
    rows = []
    for category, base_weight in category_weights.items():
        rows.append(
            {
                "分类": CATEGORY_LABELS.get(category, category),
                "基础权重": float(base_weight),
                "互动调整": float(interaction_adjustments.get(category, 0)),
                "综合兴趣": float(base_weight)
                + float(interaction_adjustments.get(category, 0)),
            }
        )
    if rows:
        frame = pd.DataFrame(rows).set_index("分类")
        with st.container(border=True):
            st.markdown(
                render_card_header_html(
                    "分类兴趣分布",
                    "基础偏好与互动调整合并后的分类权重。",
                ),
                unsafe_allow_html=True,
            )
            st.bar_chart(frame[["综合兴趣"]])
            st.dataframe(frame, width="stretch")

    keyword_adjustments = dict(
        profile.get("interaction_keyword_adjustments") or {}
    )
    positive = sorted(
        (
            {"关键词": key, "互动权重": value}
            for key, value in keyword_adjustments.items()
            if value > 0
        ),
        key=lambda row: row["互动权重"],
        reverse=True,
    )
    negative = sorted(
        (
            {"关键词": key, "互动权重": value}
            for key, value in keyword_adjustments.items()
            if value < 0
        ),
        key=lambda row: row["互动权重"],
    )
    comment_topics = sorted(
        dict(profile.get("comment_topic_counts") or {}).items(),
        key=lambda pair: pair[1],
        reverse=True,
    )
    has_interactions = bool(
        like_counts
        or favorite_counts
        or comment_counts
        or keyword_adjustments
        or comment_topics
    )
    if not has_interactions:
        st.markdown(
            render_empty_state_html(
                "还没有足够数据",
                "点赞、收藏或评论几条新闻后，系统会逐渐形成你的偏好画像。",
                "◌",
            ),
            unsafe_allow_html=True,
        )
        return

    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        with st.container(border=True):
            st.markdown(
                render_card_header_html(
                    "最感兴趣关键词",
                    "互动带来正向权重的主题。",
                ),
                unsafe_allow_html=True,
            )
            if positive:
                st.dataframe(
                    pd.DataFrame(positive[:10]),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("暂无正向关键词。")
    with col2:
        with st.container(border=True):
            st.markdown(
                render_card_header_html(
                    "不感兴趣关键词",
                    "互动带来负向权重的主题。",
                ),
                unsafe_allow_html=True,
            )
            if negative:
                st.dataframe(
                    pd.DataFrame(negative[:10]),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("暂无负向关键词。")
    with col3:
        with st.container(border=True):
            st.markdown(
                render_card_header_html(
                    "评论最多主题",
                    "你讨论最频繁的新闻主题。",
                ),
                unsafe_allow_html=True,
            )
            if comment_topics:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"主题": key, "评论次数": count}
                            for key, count in comment_topics[:10]
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.caption("暂无评论主题。")

    focus_categories = [
        CATEGORY_LABELS.get(category, category)
        for category, _ in sorted(
            interaction_adjustments.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if interaction_adjustments[category] > 0
    ][:3]
    focus_keywords = [row["关键词"] for row in positive[:5]]
    if focus_categories or focus_keywords:
        explanation = (
            "根据你的点赞、收藏和评论记录，系统判断你目前更关注："
            + "、".join(focus_categories + focus_keywords)
            + "。后续生成日报时，这些主题会获得更高排序权重。"
        )
        st.markdown(
            '<div class="shad-card">'
            + render_card_header_html(
                "画像解释",
                explanation,
                "i",
            )
            + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            render_empty_state_html(
                "画像仍在形成",
                "继续点赞、收藏或评论，系统会逐步学习你的关注偏好。",
                "◌",
            ),
            unsafe_allow_html=True,
        )


def _run_from_page(send_email: bool) -> None:
    label = "发送日报" if send_email else "生成日报"
    with st.spinner(f"正在{label}，可能需要几分钟……"):
        try:
            result = run_digest_command(
                PROJECT_ROOT,
                send_email=send_email,
            )
        except Exception as exc:
            st.error(f"启动失败：{type(exc).__name__}")
            return
    if int(result["returncode"]) == 0:
        st.success(f"{label}完成。")
    else:
        st.error(f"{label}失败，请查看输出。")
    st.code(
        str(result["stdout"]) + str(result["stderr"]) or "命令没有输出。",
        language="text",
    )


def page_email(settings) -> None:
    page_header(
        "设置",
        "调整邮件推送与省 API 生成参数。",
    )
    values = get_email_settings(settings.database_path)
    latest_run = get_latest_scheduler_run(settings.database_path)
    configured = email_configuration_complete(settings)
    generation = get_generation_settings(
        settings.filtering,
        settings.database_path,
    )

    st.markdown(
        '<div class="shad-alert">'
        '<div class="shad-alert-icon">i</div><div>'
        '<div class="shad-alert-title">本地调度说明</div>'
        '<div class="shad-alert-description">'
        "本地定时邮件只在电脑开机且调度器运行时生效。"
        "GitHub Actions 的发送时间仍由工作流 cron 独立控制。"
        "</div></div></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        render_metric_card(
            "✓" if configured else "!",
            "邮箱配置",
            "完整" if configured else "不完整",
            "页面不会显示授权码",
        )
    with c2:
        render_metric_card(
            "◷",
            "本地自动发送",
            "已启用"
            if values["auto_send_local_enabled"]
            else "未启用",
            "依赖本机调度器",
        )
    with c3:
        render_metric_card(
            "·",
            "最近调度结果",
            str(latest_run["status"]) if latest_run else "暂无记录",
            "最近一次本地运行",
        )

    with st.container(border=True):
        st.markdown(
            render_card_header_html(
                "邮件推送设置",
                "配置发送开关、时间、时区和本地自动调度。",
            ),
            unsafe_allow_html=True,
        )
        with st.form("email_settings_form", border=False):
            email_enabled = st.toggle(
                "启用邮件推送",
                value=bool(values["email_enabled"]),
            )
            e1, e2 = st.columns(2)
            send_time = e1.time_input(
                "每日发送时间",
                value=parse_send_time(values["email_send_time"]),
                step=60,
            )
            timezone_name = e2.text_input(
                "时区",
                value=str(values["timezone"]),
                help="使用 IANA 时区，例如 Asia/Singapore 或 Asia/Shanghai。",
            )
            auto_send = st.toggle(
                "启用本地自动发送",
                value=bool(values["auto_send_local_enabled"]),
            )
            if st.form_submit_button(
                "保存邮件设置",
                type="primary",
            ):
                try:
                    ZoneInfo(timezone_name)
                except ZoneInfoNotFoundError:
                    st.error(
                        "时区无效，请输入 Asia/Singapore 这类 IANA 时区。"
                    )
                else:
                    save_email_settings(
                        email_enabled,
                        send_time.strftime("%H:%M"),
                        timezone_name,
                        auto_send,
                        settings.database_path,
                    )
                    st.success(
                        "邮件设置已保存。若刚开启本地自动发送，请重新运行 "
                        "`python scripts/start_web.py` 以启动调度器。"
                    )
                    st.rerun()

    with st.container(border=True):
        st.markdown(
            render_card_header_html(
                "生成设置",
                "控制新闻数量、AI 精评范围、语言和背景补充。",
            ),
            unsafe_allow_html=True,
        )
        st.caption("设置保存在本机 SQLite，不会写入 GitHub 或显示密钥。")
        with st.form("generation_settings_form", border=False):
            low_api_mode = st.toggle(
                "省 API 模式",
                value=bool(generation["low_api_mode"]),
                help="只对规则分较高的候选新闻执行 DeepSeek 精评。",
            )
            g1, g2, g3 = st.columns(3)
            max_total_news = g1.number_input(
                "新闻总数",
                min_value=5,
                max_value=30,
                value=int(generation["max_total_news"]),
                step=1,
            )
            max_items_per_category = g2.number_input(
                "每类最多",
                min_value=1,
                max_value=8,
                value=int(generation["max_items_per_category"]),
                step=1,
            )
            pre_ai_prefilter_limit = g3.number_input(
                "AI 精评候选",
                min_value=10,
                max_value=120,
                value=int(generation["pre_ai_prefilter_limit"]),
                step=5,
            )
            g4, g5, g6 = st.columns(3)
            enable_bilingual_report = g4.toggle(
                "双语日报",
                value=bool(generation["enable_bilingual_report"]),
            )
            enable_enrichment = g5.toggle(
                "背景补充",
                value=bool(generation["enable_enrichment"]),
            )
            max_enriched_items = g6.number_input(
                "背景补充数量",
                min_value=1,
                max_value=3,
                value=int(generation["max_enriched_items"]),
                step=1,
                disabled=not enable_enrichment,
            )
            if st.form_submit_button(
                "保存生成设置",
                type="primary",
            ):
                save_generation_settings(
                    low_api_mode,
                    int(max_total_news),
                    int(max_items_per_category),
                    int(pre_ai_prefilter_limit),
                    enable_bilingual_report,
                    enable_enrichment,
                    int(max_enriched_items),
                    settings.database_path,
                )
                st.success("生成设置已保存，下次生成日报时生效。")
                st.rerun()

    with st.container(border=True):
        st.markdown(
            render_card_header_html(
                "手动操作",
                "生成测试日报，或在确认后立即发送邮件。",
            ),
            unsafe_allow_html=True,
        )
        st.caption("页面不会显示 DEEPSEEK_API_KEY 或 SMTP_PASSWORD。")
        col1, col2 = st.columns(2)
        if col1.button(
            "生成但不发送",
            key="email_dry_run",
            width="stretch",
        ):
            _run_from_page(False)
        confirm_send = col2.checkbox(
            "确认立即发送测试日报",
            key="confirm_send",
        )
        if col2.button(
            "立即发送一封测试日报",
            disabled=not confirm_send or not configured,
            key="email_test_send",
            type="primary",
            width="stretch",
        ):
            _run_from_page(True)


def page_generate(settings) -> None:
    page_header("手动生成日报", "立即运行现有 RSS 抓取和日报生成流程。")
    st.write("此操作等价于 `python -m src.main --dry-run`，不会发送邮件。")
    confirmed = st.checkbox(
        "我确认立即生成，并允许更新今天的本地日报记录",
        key="generate_confirm",
    )
    if st.button(
        "🚀 立即生成今日日报",
        disabled=not confirmed,
        key="generate_now",
    ):
        _run_from_page(False)


def main() -> None:
    inject_styles()
    try:
        settings = app_settings()
        initialize_database(settings.database_path)
    except (ConfigError, RuntimeError, OSError) as exc:
        st.error(f"应用初始化失败：{exc}")
        st.stop()

    if "page" not in st.session_state:
        st.session_state["page"] = PAGE_HOME

    handlers = {
        PAGE_HOME: render_home,
        PAGE_RADAR: page_radar,
        PAGE_TODAY: page_today,
        PAGE_HISTORY: page_history,
        PAGE_INTERACTIONS: page_interactions,
        PAGE_FAVORITES: page_favorites,
        PAGE_PROFILE: page_profile,
        PAGE_EMAIL: page_email,
        PAGE_GENERATE: page_generate,
    }
    page = st.session_state.get("page", PAGE_HOME)
    handlers.get(page, render_home)(settings)


if __name__ == "__main__":
    main()
