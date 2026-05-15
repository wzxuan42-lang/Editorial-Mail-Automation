"""
Gmail API 封装：OAuth 认证、搜索投稿邮件、提取发件人
"""
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service(credentials_file: str, token_file: str):
    """
    完成 OAuth 流程并返回 Gmail API service 对象。
    首次运行会弹出浏览器授权，之后使用 token.json 自动刷新。
    """
    creds = None
    token_path = Path(token_file).expanduser()
    creds_path = Path(credentials_file).expanduser()

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning("Token 读取失败，将重新授权：%s", e)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Token 已刷新")
            except Exception as e:
                logger.warning("Token 刷新失败，将重新授权：%s", e)
                creds = None

        if not creds:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"找不到 Gmail API 凭证文件：{creds_path}\n"
                    "请从 Google Cloud Console 下载 OAuth 凭证并命名为 credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("OAuth 授权完成")

        try:
            token_path.write_text(creds.to_json(), encoding="utf-8")
        except Exception as e:
            logger.warning("Token 保存失败（不影响本次运行）：%s", e)

    service = build("gmail", "v1", credentials=creds)
    logger.info("Gmail API 连接成功（reviewer）")
    return service


def search_submission_email(service, title: str) -> str | None:
    """
    在 Gmail 中搜索与作品名称匹配的投稿邮件，返回发件人邮箱。
    搜索策略：先搜主题，再搜全文，取最新一封。
    """
    clean_title = title.replace("《", "").replace("》", "").strip()

    strategies = [
        f'subject:"{clean_title}"',
        f'subject:"{title}"',
        f'"{clean_title}"',
        f'"{title}"',
    ]

    for query in strategies:
        logger.debug("Gmail 搜索：%s", query)
        try:
            result = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=5)
                .execute()
            )
        except Exception as e:
            logger.error("Gmail 搜索出错：%s", e)
            return None

        messages = result.get("messages", [])
        if not messages:
            continue

        msg_id = messages[0]["id"]
        sender = _extract_sender(service, msg_id)
        if sender:
            logger.info("「%s」→ 找到投稿邮件，发件人：%s", title, sender)
            return sender

    logger.warning("「%s」→ 未找到对应投稿邮件", title)
    return None


def _extract_sender(service, msg_id: str) -> str | None:
    """从邮件 headers 中提取 From 地址。"""
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From"])
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"].lower() == "from":
                return _parse_email_address(h["value"])
    except Exception as e:
        logger.error("提取发件人出错（msg_id=%s）：%s", msg_id, e)
    return None


def _parse_email_address(from_header: str) -> str:
    """从 'Name <email@example.com>' 格式中提取纯邮箱地址。"""
    if "<" in from_header and ">" in from_header:
        start = from_header.index("<") + 1
        end = from_header.index(">")
        return from_header[start:end].strip()
    return from_header.strip()
