"""
构建并通过 Gmail API 发送评审反馈邮件。
通过稿件自动附加合同文件。
"""
import base64
import logging
import mimetypes
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)

_REJECT_FOOTER = (
    "未过稿不代表您的稿件不够优秀，只是杂志有所取舍，"
    "望您不忘初心、继续创作。宇宙很大，生活更大，期待某一天我们还会相见。"
)

_ACCEPT_FOOTER = (
    "祝贺您过稿！请于一周之内将合同发回邮箱，"
    "邮件命名为『合同+作者真名+作品』。"
)


def build_email_body(title: str, comments: list[str], final: str) -> str:
    """按规则拼装纯文本邮件正文（模板版本，作为 AI 生成的回退方案）。"""
    lines = [f"《{title}》", "", "评审意见：", ""]

    for comment in comments:
        lines.append(comment)
        lines.append("")

    lines += ["最终结果：", final, ""]

    if "通过" in final and final != "不通过":
        lines.append(_ACCEPT_FOOTER)
    else:
        lines.append(_REJECT_FOOTER)

    return "\n".join(lines)


def _build_message(
    to: str,
    subject: str,
    body: str,
    sender_name: str,
    attachment_path: Path | None = None,
) -> dict:
    """
    构建 Gmail API 所需的 raw base64 邮件对象。
    有附件时使用 multipart/mixed，否则用纯文本。
    """
    has_attachment = attachment_path and attachment_path.exists()
    msg = MIMEMultipart("mixed") if has_attachment else MIMEMultipart("alternative")

    msg["To"] = to
    msg["Subject"] = subject
    msg["From"] = sender_name

    msg.attach(MIMEText(body, "plain", "utf-8"))

    if has_attachment:
        file_bytes = attachment_path.read_bytes()
        filename = attachment_path.name
        part = MIMEApplication(file_bytes, Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)
        logger.debug("已附加文件：%s", filename)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_feedback_email(
    service,
    to: str,
    title: str,
    comments: list[str],
    final: str,
    sender_name: str,
    subject_prefix: str,
    contract_path: Path | None = None,
    body: str | None = None,
) -> bool:
    """
    发送评审反馈邮件。

    参数：
        body - 可选的预生成正文（AI 生成）；为 None 时使用模板生成

    返回：
        True 表示发送成功，False 表示失败
    """
    subject = f"{subject_prefix}——《{title}》"
    email_body = body or build_email_body(title, comments, final)

    # 仅通过稿件附合同
    attachment = None
    if "通过" in final and final != "不通过":
        if contract_path and contract_path.exists():
            attachment = contract_path
        else:
            logger.warning("通过稿件「%s」：合同文件不存在，将不带附件发送", title)

    try:
        message = _build_message(
            to=to,
            subject=subject,
            body=email_body,
            sender_name=sender_name,
            attachment_path=attachment,
        )
        service.users().messages().send(userId="me", body=message).execute()
        logger.info("邮件已发送 → %s（《%s》 %s）", to, title, final)
        return True
    except Exception as e:
        logger.error("发送失败（《%s》 → %s）：%s", title, to, e)
        return False
