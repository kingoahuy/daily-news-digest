from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Tuple, Union

import markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


def _date_text(report_date: Union[date, datetime, str]) -> str:
    if isinstance(report_date, (date, datetime)):
        return report_date.strftime("%Y-%m-%d")
    return str(report_date)


def format_and_save_report(
    markdown_text: str,
    report_date: Union[date, datetime, str],
    reports_dir: Path = DEFAULT_REPORTS_DIR,
) -> Tuple[str, str, Path]:
    """保存 Markdown，并生成适合邮件阅读的完整 HTML。"""

    reports_dir.mkdir(parents=True, exist_ok=True)
    date_text = _date_text(report_date)
    report_path = reports_dir / f"daily_news_{date_text}.md"
    report_path.write_text(markdown_text, encoding="utf-8")

    body = markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(f"今日早间热点新闻日报｜{date_text}")}</title>
  <style>
    h1, h2, h3 {{ line-height: 1.35; margin: 1.4em 0 0.55em; }}
    p {{ margin: 0.75em 0; }}
    ul, ol {{ margin: 0.75em 0; padding-left: 1.5em; }}
    li {{ margin: 0.45em 0; }}
    a {{ color: #175cd3; }}
  </style>
</head>
<body style="margin:0;background:#f4f6f8;color:#202124;font-family:Arial,'Microsoft YaHei',sans-serif;line-height:1.7;">
  <div style="max-width:760px;margin:24px auto;padding:28px;background:#ffffff;border-radius:8px;">
    <div style="font-size:16px;">
      {body}
    </div>
  </div>
</body>
</html>
"""
    return markdown_text, html_text, report_path
