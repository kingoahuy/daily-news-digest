"""Check GitHub Actions environment variables without exposing their values."""

import argparse
import os
from pathlib import Path
from typing import Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEND_REQUIRED = (
    "DEEPSEEK_API_KEY",
    "SMTP_HOST",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
)
DRY_RUN_REQUIRED = ("DEEPSEEK_API_KEY",)
DEFAULTED = {
    "DEEPSEEK_BASE_URL": "程序默认值",
    "DEEPSEEK_MODEL": "程序默认值",
    "SMTP_PORT": "465",
    "TIMEZONE": "config/app.yaml",
}
SMTP_VARIABLES = {
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
}
OPTIONAL = (
    "MAX_NEWS_PER_CATEGORY",
    "NEWS_LOOKBACK_HOURS",
)
CHECKED_VARIABLES = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
    "TIMEZONE",
    *OPTIONAL,
)


def _configured(environ: Mapping[str, str], name: str) -> bool:
    return bool(str(environ.get(name, "")).strip())


def check_environment(mode: str, environ: Mapping[str, str]) -> bool:
    """Print configuration status and return whether critical values are valid."""

    required = set(SEND_REQUIRED if mode == "send" else DRY_RUN_REQUIRED)
    missing = []
    invalid = []

    print(f"GitHub Actions 环境预检：mode={mode}")
    for name in CHECKED_VARIABLES:
        if _configured(environ, name):
            print(f"[OK] {name} 已配置")
        elif name in required:
            missing.append(name)
            print(f"[MISSING] {name} 未配置")
        elif mode == "dry-run" and name in SMTP_VARIABLES:
            print(f"[SKIP] {name} 未配置，dry-run 不需要")
        elif name in DEFAULTED:
            print(f"[DEFAULT] {name} 未配置，将使用 {DEFAULTED[name]}")
        else:
            print(f"[OPTIONAL] {name} 未配置")

    raw_port = str(environ.get("SMTP_PORT", "")).strip()
    if mode == "send" and raw_port:
        try:
            port = int(raw_port)
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            invalid.append("SMTP_PORT")
            print("[INVALID] SMTP_PORT 必须是 1-65535 的整数")

    timezone_name = str(environ.get("TIMEZONE", "")).strip()
    if timezone_name:
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            invalid.append("TIMEZONE")
            print("[INVALID] TIMEZONE 必须是有效的 IANA 时区名称")

    if missing or invalid:
        print("-" * 60)
        print("环境预检失败。请进入 GitHub 仓库的：")
        print("Settings -> Secrets and variables -> Actions")
        if missing:
            print("需要新增或检查这些 Repository secrets：")
            for name in missing:
                print(f"- {name}")
        if invalid:
            print("需要修正这些变量的格式：")
            for name in invalid:
                print(f"- {name}")
        if "SMTP_PASSWORD" in missing:
            print("SMTP_PASSWORD 应填写邮箱 SMTP 授权码，不是网页登录密码。")
        return False

    print("-" * 60)
    print("环境预检通过，未输出任何 Secret 内容。")
    return True


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查日报工作流环境变量。")
    parser.add_argument(
        "--mode",
        choices=("dry-run", "send"),
        default=os.getenv("ACTIONS_RUN_MODE", "send"),
        help="dry-run 只要求 DeepSeek；send 同时要求 SMTP 配置。",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if os.getenv("GITHUB_ACTIONS", "").strip().lower() != "true":
        load_dotenv(PROJECT_ROOT / ".env")
    return 0 if check_environment(args.mode, os.environ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
