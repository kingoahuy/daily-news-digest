import argparse
import shutil
from pathlib import Path
from typing import Dict, List

from src.config import PROJECT_ROOT, Settings, load_settings


def _project_path(value: object, default: Path) -> Path:
    text = str(value or "").strip()
    if not text:
        return default
    path = Path(text).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def export_pages(
    reports_dir: Path,
    docs_dir: Path,
    docs_reports_dir: Path,
    project_title: str = "个人 AI 新闻雷达",
) -> Dict[str, object]:
    """复制日报并生成适合 GitHub Pages/Jekyll 的静态索引。"""

    reports_dir = Path(reports_dir)
    docs_dir = Path(docs_dir)
    docs_reports_dir = Path(docs_reports_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    docs_reports_dir.mkdir(parents=True, exist_ok=True)

    report_paths = sorted(
        reports_dir.glob("daily_news_*.md"),
        key=lambda path: path.name,
        reverse=True,
    )
    copied: List[Path] = []
    for source in report_paths:
        destination = docs_reports_dir / source.name
        shutil.copy2(source, destination)
        copied.append(destination)

    relative_reports_dir = docs_reports_dir.relative_to(docs_dir)
    lines = [
        "---",
        "layout: default",
        f'title: "{project_title}"',
        "---",
        "",
        f"# {project_title} / Personal AI News Radar",
        "",
        "这是自动生成的新闻简报归档。内容来自 RSS 标题、摘要和原始链接，"
        "不会抓取新闻全文。",
        "",
        "This is an automatically generated bilingual news digest archive. "
        "It uses RSS titles, summaries, and source links without fetching full articles.",
        "",
    ]
    if copied:
        latest = copied[0]
        latest_label = latest.stem.replace("daily_news_", "")
        latest_link = (relative_reports_dir / latest.name).as_posix()
        lines.extend(
            [
                "## 最新日报 / Latest Digest",
                "",
                f"- [{latest_label}]({latest_link})",
                "",
                "## 历史日报 / Archive",
                "",
            ]
        )
        for path in copied:
            label = path.stem.replace("daily_news_", "")
            link = (relative_reports_dir / path.name).as_posix()
            lines.append(f"- [{label}]({link})")
    else:
        lines.extend(
            [
                "## 历史日报 / Archive",
                "",
                "尚未生成日报。 / No digest has been generated yet.",
            ]
        )
    lines.append("")
    (docs_dir / "index.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    (docs_dir / "_config.yml").write_text(
        "\n".join(
            [
                f'title: "{project_title}"',
                'description: "Bilingual personal AI news radar archive"',
                'theme: "jekyll-theme-cayman"',
                "markdown: kramdown",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "copied_count": len(copied),
        "index_path": docs_dir / "index.md",
        "docs_dir": docs_dir,
    }


def export_pages_from_settings(settings: Settings) -> Dict[str, object]:
    page_config = dict(settings.delivery.get("github_pages") or {})
    docs_dir = _project_path(
        page_config.get("docs_dir"),
        PROJECT_ROOT / "docs",
    )
    docs_reports_dir = _project_path(
        page_config.get("reports_dir"),
        docs_dir / "reports",
    )
    title = str(
        settings.app_config.get("project_title", "个人 AI 新闻雷达")
    )
    return export_pages(
        PROJECT_ROOT / "reports",
        docs_dir,
        docs_reports_dir,
        title,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 GitHub Pages 静态日报。")
    parser.parse_args()
    settings = load_settings(send_email=False, require_api_key=False)
    result = export_pages_from_settings(settings)
    print(
        f"GitHub Pages 导出完成：{result['copied_count']} 篇日报，"
        f"索引={Path(result['index_path']).resolve()}"
    )


if __name__ == "__main__":
    main()
