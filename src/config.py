import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


class ConfigError(ValueError):
    """配置不完整或格式错误。"""


@dataclass(frozen=True)
class Settings:
    """程序运行需要的全部配置。"""

    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    mail_from: str
    mail_to: str
    timezone: str
    max_news_per_category: int
    news_lookback_hours: int


def _get_env(name: str, default: str = "") -> str:
    """读取并清理环境变量；空字符串视为没有配置。"""

    value = os.getenv(name, "").strip()
    return value or default


def _positive_int(name: str, default: int) -> int:
    raw_value = _get_env(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} 必须是整数，当前值为：{raw_value!r}。") from exc

    if value <= 0:
        raise ConfigError(f"{name} 必须大于 0。")
    return value


def load_settings(send_email: bool = False) -> Settings:
    """从 .env 和系统环境变量加载配置。

    dry-run 只要求 DeepSeek API Key；send 模式还会检查 SMTP 配置。
    """

    load_dotenv()

    deepseek_api_key = _get_env("DEEPSEEK_API_KEY")
    required_values = {"DEEPSEEK_API_KEY": deepseek_api_key}

    smtp_values = {
        "SMTP_HOST": _get_env("SMTP_HOST"),
        "SMTP_USER": _get_env("SMTP_USER"),
        "SMTP_PASSWORD": _get_env("SMTP_PASSWORD"),
        "MAIL_FROM": _get_env("MAIL_FROM"),
        "MAIL_TO": _get_env("MAIL_TO"),
    }
    if send_email:
        required_values.update(smtp_values)

    missing = [name for name, value in required_values.items() if not value]
    if missing:
        names = "、".join(missing)
        raise ConfigError(
            f"缺少 {names}，请在 .env 或 GitHub Secrets 中配置。"
        )

    timezone_name = _get_env("TIMEZONE", "Asia/Singapore")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(
            f"TIMEZONE 无效：{timezone_name!r}，请使用 Asia/Singapore 这类 IANA 时区名称。"
        ) from exc

    smtp_port = _positive_int("SMTP_PORT", 465) if send_email else 465

    return Settings(
        deepseek_api_key=deepseek_api_key,
        deepseek_base_url=_get_env(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        ),
        deepseek_model=_get_env("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        smtp_host=smtp_values["SMTP_HOST"],
        smtp_port=smtp_port,
        smtp_user=smtp_values["SMTP_USER"],
        smtp_password=smtp_values["SMTP_PASSWORD"],
        mail_from=smtp_values["MAIL_FROM"],
        mail_to=smtp_values["MAIL_TO"],
        timezone=timezone_name,
        max_news_per_category=_positive_int("MAX_NEWS_PER_CATEGORY", 8),
        news_lookback_hours=_positive_int("NEWS_LOOKBACK_HOURS", 36),
    )
