import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    database_path: Path
    feeds_path: Path
    preferences_path: Path
    app_config_path: Path
    filtering_path: Path
    delivery_path: Path
    app_config: Dict[str, Any]
    filtering: Dict[str, Any]
    delivery: Dict[str, Any]


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


def _project_path(name: str, default: Path) -> Path:
    raw_value = _get_env(name)
    if not raw_value:
        return default

    path = Path(raw_value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _source_config_path() -> Path:
    explicit = _get_env("SOURCES_PATH")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else PROJECT_ROOT / path

    v4_default = PROJECT_ROOT / "config" / "sources.yaml"
    if v4_default.exists():
        return v4_default
    return _project_path(
        "FEEDS_PATH",
        PROJECT_ROOT / "config" / "feeds.yaml",
    )


def _load_yaml(path: Path, label: str) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"无法读取{label} {path}：{exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{label}格式错误：顶层必须是对象。")
    return data


def _configured_int(
    env_name: str,
    config: Dict[str, Any],
    config_key: str,
    default: int,
) -> int:
    raw_value = _get_env(env_name)
    if not raw_value:
        raw_value = str(config.get(config_key, default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"{env_name}/{config_key} 必须是整数，当前值为：{raw_value!r}。"
        ) from exc
    if value <= 0:
        raise ConfigError(f"{env_name}/{config_key} 必须大于 0。")
    return value


def _missing_settings_message(missing: list[str]) -> str:
    lines = [
        "缺少以下必要配置：",
        *(f"- {name}" for name in missing),
        "",
        "本地运行：请在项目根目录的 .env 中配置。",
        "GitHub Actions：请进入仓库 Settings -> Secrets and variables "
        "-> Actions -> New repository secret，逐项添加同名 Secret。",
    ]
    if "DEEPSEEK_API_KEY" in missing:
        lines.append("DEEPSEEK_API_KEY 应填写有效的 DeepSeek API Key。")
    if "SMTP_PASSWORD" in missing:
        lines.append(
            "SMTP_PASSWORD 应填写邮箱 SMTP 授权码，不是邮箱网页登录密码。"
        )
    lines.append("安全提示：程序不会打印 Secret 的真实内容。")
    return "\n".join(lines)


def load_settings(
    send_email: bool = False,
    require_api_key: bool = True,
) -> Settings:
    """从 .env 和系统环境变量加载配置。

    主流程默认要求 DeepSeek API Key；网页端只读配置时可以关闭这项检查。
    send 模式还会检查 SMTP 配置。
    """

    load_dotenv()

    app_config_path = _project_path(
        "APP_CONFIG_PATH", PROJECT_ROOT / "config" / "app.yaml"
    )
    filtering_path = _project_path(
        "FILTERING_PATH", PROJECT_ROOT / "config" / "filtering.yaml"
    )
    delivery_path = _project_path(
        "DELIVERY_PATH", PROJECT_ROOT / "config" / "delivery.yaml"
    )
    app_config = _load_yaml(app_config_path, "应用配置")
    filtering = _load_yaml(filtering_path, "过滤配置")
    delivery = _load_yaml(delivery_path, "投递配置")

    deepseek_api_key = _get_env("DEEPSEEK_API_KEY")
    required_values = {}
    if require_api_key:
        required_values["DEEPSEEK_API_KEY"] = deepseek_api_key

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
        raise ConfigError(_missing_settings_message(missing))

    timezone_name = _get_env(
        "TIMEZONE",
        str(app_config.get("timezone", "Asia/Singapore")),
    )
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
        max_news_per_category=_configured_int(
            "MAX_NEWS_PER_CATEGORY",
            filtering,
            "max_items_per_category",
            3,
        ),
        news_lookback_hours=_configured_int(
            "NEWS_LOOKBACK_HOURS",
            filtering,
            "time_window_hours",
            24,
        ),
        database_path=_project_path(
            "DATABASE_PATH", PROJECT_ROOT / "data" / "news_digest.db"
        ),
        feeds_path=_source_config_path(),
        preferences_path=_project_path(
            "PREFERENCES_PATH", PROJECT_ROOT / "config" / "preferences.yaml"
        ),
        app_config_path=app_config_path,
        filtering_path=filtering_path,
        delivery_path=delivery_path,
        app_config=app_config,
        filtering=filtering,
        delivery=delivery,
    )
