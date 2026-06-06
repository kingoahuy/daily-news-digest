import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Union

from src.config import Settings


def _date_text(report_date: Union[date, datetime, str]) -> str:
    if isinstance(report_date, (date, datetime)):
        return report_date.strftime("%Y-%m-%d")
    return str(report_date)


def send_email(
    settings: Settings,
    markdown_text: str,
    html_text: str,
    report_date: Union[date, datetime, str],
    dry_run: bool = False,
) -> bool:
    """发送包含纯文本和 HTML 两种正文的邮件。"""

    if dry_run:
        print("dry-run 模式：日报已生成，但没有发送邮件。")
        return False

    recipients = [
        address.strip() for address in settings.mail_to.split(",") if address.strip()
    ]
    message = MIMEMultipart("alternative")
    message["Subject"] = f"今日早间热点新闻日报｜{_date_text(report_date)}"
    message["From"] = settings.mail_from
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(markdown_text, "plain", "utf-8"))
    message.attach(MIMEText(html_text, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=30
        ) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.mail_from, recipients, message.as_string())
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError(
            f"邮件发送失败，请检查 SMTP 主机、端口、账号和授权码：{exc}"
        ) from exc

    print("邮件发送成功。")
    return True
