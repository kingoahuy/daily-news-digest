from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import streamlit as st

from src.config import ConfigError, load_settings
from src.database import (
    add_comment,
    get_email_settings,
    get_favorite_news,
    get_interaction_state,
    get_interaction_summary,
    get_latest_report,
    get_latest_scheduler_run,
    get_news_comments,
    get_news_items,
    initialize_database,
    list_reports,
    save_email_settings,
    toggle_favorite,
    toggle_like,
)
from src.preference import build_user_preference_profile
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
    PAGE_EMAIL: "邮件推送设置",
    PAGE_GENERATE: "手动生成日报",
}

st.set_page_config(
    page_title="个人 AI 新闻雷达",
    page_icon="📰",
    layout="wide",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f6f8fb; }
        .block-container { max-width: 1180px; padding-top: 2rem; }
        .hero {
            padding: 1.8rem 2rem;
            border-radius: 18px;
            color: white;
            background: linear-gradient(125deg, #173f73, #2575b8);
            box-shadow: 0 12px 32px rgba(23, 63, 115, 0.18);
            margin-bottom: 1.2rem;
        }
        .hero h1 { margin: 0 0 .45rem; font-size: 2.15rem; }
        .hero p { margin: 0; color: #e7f1fb; font-size: 1.04rem; }
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e8edf3;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 4px 16px rgba(30, 60, 90, .05);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: white;
            border-color: #e7ebf0;
            border-radius: 16px;
            box-shadow: 0 5px 18px rgba(30, 60, 90, .05);
        }
        .section-note { color: #667085; margin-top: -.4rem; }
        .news-title { font-size: 1.08rem; font-weight: 700; color: #17324d; }
        .news-meta { color: #667085; font-size: .88rem; }
        .status-line { color: #475467; font-size: .88rem; }
        .tag {
            display: inline-block; padding: .2rem .55rem; margin: .1rem .18rem .1rem 0;
            border-radius: 999px; background: #eef4ff; color: #175cd3; font-size: .78rem;
        }
        .ai-reason {
            padding: .75rem .9rem; margin: .65rem 0; border-radius: 10px;
            background: #f0f7ff; border-left: 4px solid #2e90fa; color: #344054;
        }
        .cluster-line { color: #6941c6; font-size: .86rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource
def app_settings():
    return load_settings(send_email=False, require_api_key=False)


def go_to(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()


def page_header(title: str, description: str = "") -> None:
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title(title)
        if description:
            st.markdown(
                f'<p class="section-note">{description}</p>',
                unsafe_allow_html=True,
            )
    with col2:
        if st.button("← 返回首页", key=f"back_{st.session_state['page']}"):
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
    col1, col2, col3 = st.columns(3)
    col1.metric("日报日期", str(report["report_date"]))
    col2.metric("生成时间", display_time(report["generated_at"]))
    col3.metric(
        "邮件状态",
        "已发送" if int(report["email_sent"]) else "未发送",
    )
    st.info(f"核心议题：{report['core_topic'] or '未记录'}")


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

    with st.container(border=True):
        st.markdown(
            f'<div class="news-title">{news_item["title"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="news-meta">'
            f'{category} · {news_item.get("source") or "未知来源"} · '
            f'{display_time(news_item.get("published_at"))} · '
            f'AI 重要性 {float(news_item.get("ai_score") or news_item.get("score") or 0):.2f}/10 · '
            f'个性化排序 {float(news_item.get("score") or 0):.2f}'
            "</div>",
            unsafe_allow_html=True,
        )
        st.write(news_item.get("summary") or "RSS 未提供摘要。")
        ai_summary = str(news_item.get("ai_summary") or "").strip()
        if ai_summary and ai_summary != str(news_item.get("summary") or ""):
            st.markdown("**AI 双语摘要 / AI bilingual summary**")
            st.write(ai_summary)
        ai_reason = str(news_item.get("ai_reason") or "").strip()
        if ai_reason:
            st.markdown(
                f'<div class="ai-reason"><strong>AI 推荐理由 / Why it matters</strong><br>'
                f'{ai_reason}</div>',
                unsafe_allow_html=True,
            )
        tags = ai_tags or keywords
        if tags:
            st.markdown(
                "".join(f'<span class="tag">{word}</span>' for word in tags),
                unsafe_allow_html=True,
            )
        if news_item.get("cluster_title"):
            st.markdown(
                '<div class="cluster-line">'
                f'主题簇 / Story cluster：{news_item["cluster_title"]}'
                "</div>",
                unsafe_allow_html=True,
            )
        if enrichment:
            with st.expander("核心新闻背景 / Core story context"):
                for key, label in (
                    ("whats_new", "最新变化 / What's new"),
                    ("why_it_matters", "为何重要 / Why it matters"),
                    ("background", "背景 / Background"),
                    ("possible_impact", "可能影响 / Possible impact"),
                ):
                    value = str(enrichment.get(key) or "").strip()
                    if value:
                        st.markdown(f"**{label}**")
                        st.write(value)
                points = enrichment.get("follow_up_points") or []
                if points:
                    st.markdown("**后续看点 / Follow-up points**")
                    for point in points:
                        st.markdown(f"- {point}")
        st.markdown(f"[查看原文]({news_item['url']})")

        if not show_interactions:
            return

        state = get_interaction_state(news_id, db_path)
        like_label = "👍 取消点赞" if state["liked"] else "👍 点赞"
        favorite_label = (
            "⭐ 取消收藏" if state["favorited"] else "⭐ 收藏"
        )
        col1, col2, col3 = st.columns([1, 1, 3])
        if col1.button(like_label, key=f"like_{unique_key}"):
            active = toggle_like(news_id, report_id, db_path)
            st.toast("已点赞" if active else "已取消点赞")
            st.rerun()
        if col2.button(favorite_label, key=f"favorite_{unique_key}"):
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

        st.markdown(
            '<div class="status-line">'
            f'{"已点赞" if state["liked"] else "未点赞"} · '
            f'{"已收藏" if state["favorited"] else "未收藏"} · '
            f'{state["comment_count"]} 条评论'
            "</div>",
            unsafe_allow_html=True,
        )

        if st.session_state.get(f"comment_open_{unique_key}", False):
            comment = st.text_area(
                "写下你的想法",
                key=f"comment_text_{unique_key}",
                placeholder="例如：重要，继续关注这个主题。",
            )
            if st.button("保存评论", key=f"comment_save_{unique_key}"):
                if not comment.strip():
                    st.warning("评论内容为空，未保存。")
                else:
                    add_comment(news_id, report_id, comment, db_path)
                    st.session_state[f"comment_open_{unique_key}"] = False
                    st.toast("评论已保存")
                    st.rerun()

            comments = get_news_comments(news_id, db_path)
            if comments:
                st.caption("已有评论")
                for row in comments:
                    st.markdown(
                        f"- {row['action_value']}  "
                        f"`{display_time(row['created_at'])}`"
                    )


def render_home(settings) -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>个人 AI 新闻雷达</h1>
          <p>Personal AI News Radar · 双语评分、主题聚类、背景补充与个性化推荐。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    col1, col2, col3, col4 = st.columns(4)
    report_status = "已生成" if is_today else "未生成"
    if is_today:
        report_status += " · " + (
            "邮件已发送" if int(latest["email_sent"]) else "邮件未发送"
        )
    col1.metric("今日日报状态", report_status)
    col2.metric("今日新闻数量", len(today_items))
    col3.metric(
        "我的互动记录",
        interactions["total"],
        f"赞 {interactions['like']} · 藏 {interactions['favorite']} · 评 {interactions['comment']}",
    )
    col4.metric(
        "下次邮件时间",
        next_email_time_text(
            email_settings["email_send_time"],
            str(email_settings["timezone"]),
            bool(
                email_settings["email_enabled"]
                and email_settings["auto_send_local_enabled"]
            ),
        ),
    )

    st.subheader("功能入口")
    cards = [
        (
            PAGE_RADAR,
            "📡",
            "AI 新闻雷达",
            "查看高分新闻、主题聚类、过滤统计和偏好影响。",
        ),
        (PAGE_TODAY, "📌", "今日日报", "查看今天生成的完整新闻简报。"),
        (PAGE_HISTORY, "📚", "历史日报", "按日期回看历史新闻报告。"),
        (
            PAGE_INTERACTIONS,
            "👍",
            "新闻互动",
            "点赞、收藏和评论，让系统学习你的偏好。",
        ),
        (PAGE_FAVORITES, "⭐", "我的收藏", "集中查看收藏过的重要新闻。"),
        (PAGE_PROFILE, "🧠", "我的偏好画像", "查看系统如何理解你的新闻兴趣。"),
        (PAGE_EMAIL, "⏰", "邮件推送设置", "设置本地每日邮件自动发送时间。"),
        (PAGE_GENERATE, "🚀", "手动生成日报", "立即抓取新闻并生成今日报告。"),
    ]
    for start in range(0, len(cards), 3):
        columns = st.columns(3)
        for column, card in zip(columns, cards[start : start + 3]):
            page, icon, title, description = card
            with column:
                with st.container(border=True):
                    st.markdown(f"### {icon} {title}")
                    st.write(description)
                    if st.button(
                        f"进入{title}",
                        key=f"home_nav_{page}",
                        width="stretch",
                    ):
                        go_to(page)


def page_radar(settings) -> None:
    page_header(
        "AI 新闻雷达",
        "AI News Radar · 查看评分、主题聚类、阈值过滤和个性化排序影响。",
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("今日高分新闻", len(high_items))
    c2.metric("低分过滤", int(stats.get("filtered_count", 0)))
    c3.metric("主题聚类", int(stats.get("cluster_count", 0)))
    c4.metric(
        "多来源主题",
        int(stats.get("multi_source_cluster_count", 0)),
    )

    category_averages = dict(stats.get("category_averages") or {})
    if category_averages:
        st.subheader("各分类平均 AI 分 / Average AI score by category")
        category_frame = pd.DataFrame(
            [
                {
                    "分类": CATEGORY_LABELS.get(category, category),
                    "平均 AI 分": float(score),
                }
                for category, score in category_averages.items()
            ]
        ).set_index("分类")
        st.bar_chart(category_frame)
        st.dataframe(category_frame, width="stretch")

    impact = dict(stats.get("preference_impact") or {})
    st.subheader("我的偏好对排序的影响 / Preference impact")
    p1, p2, p3 = st.columns(3)
    p1.metric(
        "平均分数调整",
        f"{float(impact.get('average_adjustment', 0)):+.3f}",
    )
    p2.metric("获得加分", int(impact.get("boosted_items", 0)))
    p3.metric("被降低", int(impact.get("reduced_items", 0)))

    if clusters:
        st.subheader("主题聚类结果 / Story clusters")
        cluster_frame = pd.DataFrame(
            [
                {
                    "主题": row.get("main_title", ""),
                    "来源数": len(row.get("sources") or []),
                    "关联新闻": int(row.get("related_count", 0)),
                    "聚类分": float(row.get("cluster_score", 0)),
                    "来源": " / ".join(row.get("sources") or []),
                }
                for row in clusters
            ]
        )
        st.dataframe(cluster_frame, width="stretch", hide_index=True)

    st.subheader("今日高分新闻 / Today's high-scoring stories")
    visible = sorted(
        items,
        key=lambda item: float(item.get("ai_score") or 0),
        reverse=True,
    )[:10]
    if not visible:
        st.info("本期没有可展示的高分新闻。")
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
    c1, c2, c3 = st.columns(3)
    c1.metric("点赞", summary["like"])
    c2.metric("收藏", summary["favorite"])
    c3.metric("评论", summary["comment"])

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

    c1, c2, c3 = st.columns(3)
    c1.metric("最常点赞分类", _top_category(like_counts))
    c2.metric("最常收藏分类", _top_category(favorite_counts))
    c3.metric("评论最多分类", _top_category(comment_counts))

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
    frame = pd.DataFrame(rows).set_index("分类")
    st.subheader("分类兴趣分布")
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
    col1, col2, col3 = st.columns(3)
    col1.markdown("#### 最感兴趣关键词")
    col1.dataframe(pd.DataFrame(positive[:10]), width="stretch")
    col2.markdown("#### 不感兴趣关键词")
    col2.dataframe(pd.DataFrame(negative[:10]), width="stretch")
    col3.markdown("#### 评论最多主题")
    col3.dataframe(
        pd.DataFrame(
            [{"主题": key, "评论次数": count} for key, count in comment_topics[:10]]
        ),
        width="stretch",
    )

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
        st.info(
            "根据你的点赞、收藏和评论记录，系统判断你目前更关注："
            + "、".join(focus_categories + focus_keywords)
            + "。后续生成日报时，这些主题会获得更高排序权重。"
        )
    else:
        st.info("互动数据还比较少。完成几次点赞、收藏或评论后，画像会逐步形成。")


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
        "邮件推送设置",
        "此处时间只控制本地调度器，不会修改 GitHub Actions。",
    )
    values = get_email_settings(settings.database_path)
    latest_run = get_latest_scheduler_run(settings.database_path)
    configured = email_configuration_complete(settings)

    st.warning(
        "本地定时邮件只有在电脑开机、项目网页服务或调度器正在运行时才会发送。"
        "GitHub Actions 的时间仍由 `.github/workflows/daily_news.yml` 中的 cron 控制，"
        "本页面不会实时修改 GitHub。"
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("邮箱配置", "完整" if configured else "不完整")
    c2.metric(
        "本地自动发送",
        "已启用" if values["auto_send_local_enabled"] else "未启用",
    )
    c3.metric(
        "最近调度结果",
        str(latest_run["status"]) if latest_run else "暂无记录",
    )

    with st.form("email_settings_form"):
        email_enabled = st.toggle(
            "启用邮件推送",
            value=bool(values["email_enabled"]),
        )
        send_time = st.time_input(
            "每日发送时间",
            value=parse_send_time(values["email_send_time"]),
            step=60,
        )
        timezone_name = st.text_input(
            "时区",
            value=str(values["timezone"]),
            help="使用 IANA 时区，例如 Asia/Singapore 或 Asia/Shanghai。",
        )
        auto_send = st.toggle(
            "启用本地自动发送",
            value=bool(values["auto_send_local_enabled"]),
        )
        if st.form_submit_button("保存邮件设置"):
            try:
                ZoneInfo(timezone_name)
            except ZoneInfoNotFoundError:
                st.error("时区无效，请输入 Asia/Singapore 这类 IANA 时区。")
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

    st.caption("页面不会显示 DEEPSEEK_API_KEY 或 SMTP_PASSWORD。")
    col1, col2 = st.columns(2)
    if col1.button("生成但不发送", key="email_dry_run"):
        _run_from_page(False)
    confirm_send = col2.checkbox("确认立即发送测试日报", key="confirm_send")
    if col2.button(
        "立即发送一封测试日报",
        disabled=not confirm_send or not configured,
        key="email_test_send",
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
