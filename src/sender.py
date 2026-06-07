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
    if not recipients:
        raise RuntimeError(
            "MAIL_TO 没有有效收件人，请填写一个或多个邮箱地址，多个地址用逗号分隔。"
        )
    knowledge_base_note = (
        "这份日报已保存到本地新闻知识库，可在 Streamlit 网页端查看和评价。"
    )
    email_markdown = f"{knowledge_base_note}\n\n{markdown_text}"
    email_html = html_text
    marker = '<div style="max-width:760px;'
    notice_html = (
        '<p style="padding:12px 16px;background:#eef4ff;'
        'border-radius:6px;color:#344054;">'
        f"{knowledge_base_note}</p>"
    )
    email_html = email_html.replace(marker, notice_html + marker, 1)

    message = MIMEMultipart("alternative")
    message["Subject"] = f"每日热点新闻简报｜{_date_text(report_date)}"
    message["From"] = settings.mail_from
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(email_markdown, "plain", "utf-8"))
    message.attach(MIMEText(email_html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=30
        ) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.mail_from, recipients, message.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "SMTP 登录失败（SMTPAuthenticationError）。请检查 SMTP_HOST、"
            "SMTP_PORT、SMTP_USER；确认 SMTP_PASSWORD 是邮箱 SMTP 授权码，"
            "并确认 MAIL_FROM 与 SMTP_USER 匹配或已获准代发。"
        ) from exc
    except smtplib.SMTPSenderRefused as exc:
        raise RuntimeError(
            "SMTP 服务器拒绝发件人。请检查 MAIL_FROM 是否正确，以及它是否与 "
            "SMTP_USER 匹配或已被邮箱服务商授权。"
        ) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise RuntimeError(
            "SMTP 服务器拒绝收件人。请检查 MAIL_TO 地址格式和收件地址是否有效。"
        ) from exc
    except (
        TimeoutError,
        OSError,
        smtplib.SMTPConnectError,
        smtplib.SMTPServerDisconnected,
    ) as exc:
        raise RuntimeError(
            "无法连接 SMTP 服务器。请检查 SMTP_HOST、SMTP_PORT、网络连接，"
            "并确认端口与 SSL 模式匹配。"
        ) from exc
    except smtplib.SMTPException as exc:
        raise RuntimeError(
            f"邮件发送失败（{type(exc).__name__}）。请检查 SMTP 配置和邮箱服务状态。"
        ) from exc

    print("邮件发送成功。")
    return True
