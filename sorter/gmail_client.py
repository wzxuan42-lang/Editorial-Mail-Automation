"""
Gmail API 认证与搜索模块
负责 OAuth2 登录、Token 管理、邮件列表获取、附件下载
"""
import base64
import logging
from datetime import date, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from sorter.utils import get_base_dir

logger = logging.getLogger(__name__)

# 只需读取邮件权限，遵循最小权限原则
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def get_gmail_service():
    """
    获取经过认证的 Gmail API 服务对象。
    首次运行时弹出浏览器授权页面，授权后将 Token 缓存到 token.json。
    后续运行自动刷新过期 Token，无需再次登录。
    """
    base_dir = get_base_dir()
    credentials_path = base_dir / 'credentials.json'
    token_path = base_dir / 'token.json'

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"未找到 credentials.json\n"
            f"请将文件放置于：{credentials_path}\n\n"
            f"获取方式：\n"
            f"  1. 访问 Google Cloud Console\n"
            f"  2. APIs & Services → Credentials\n"
            f"  3. 创建 OAuth 2.0 Client ID（类型选 Desktop App）\n"
            f"  4. 下载 JSON 文件并重命名为 credentials.json"
        )

    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning("Token 读取失败，将重新授权：%s", e)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("正在刷新登录状态...")
                creds.refresh(Request())
            except Exception as e:
                logger.warning("Token 刷新失败，将重新授权：%s", e)
                creds = None

        if not creds:
            logger.info("正在打开浏览器，请完成 Google 账号授权...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        try:
            token_path.write_text(creds.to_json(), encoding='utf-8')
            logger.info("授权成功，Token 已保存")
        except Exception as e:
            logger.warning("Token 保存失败（不影响本次运行）：%s", e)

    service = build('gmail', 'v1', credentials=creds)
    logger.info("Gmail API 连接成功（sorter）")
    return service


def build_search_query(start_date: str, end_date: str) -> str:
    """
    构建 Gmail 搜索语句。
    参数格式：YYYY-MM-DD
    注意：Gmail 的 before: 不包含当天，因此结束日期需加一天才能包含当天邮件。
    """
    start = start_date.replace('-', '/')
    end_dt = date.fromisoformat(end_date) + timedelta(days=1)
    end = end_dt.strftime('%Y/%m/%d')
    return f"after:{start} before:{end} has:attachment"


def search_messages(service, query: str) -> list:
    """
    执行 Gmail 搜索，自动处理分页，返回完整的邮件 ID 列表。
    单页最多 500 条，多页自动追加。
    """
    messages = []
    try:
        result = service.users().messages().list(
            userId='me', q=query, maxResults=500
        ).execute()
        messages.extend(result.get('messages', []))

        while 'nextPageToken' in result:
            result = service.users().messages().list(
                userId='me', q=query,
                pageToken=result['nextPageToken'],
                maxResults=500,
            ).execute()
            messages.extend(result.get('messages', []))

    except HttpError as e:
        logger.error("Gmail API 搜索失败：%s", e)
        raise

    return messages


def get_message_detail(service, msg_id: str) -> dict:
    """获取指定邮件的完整内容（headers、body、附件元信息）"""
    return service.users().messages().get(
        userId='me', id=msg_id, format='full'
    ).execute()


def get_attachment_data(service, msg_id: str, att_id: str) -> bytes:
    """
    下载邮件附件，返回原始字节内容。
    Gmail API 返回 base64url 无 padding 编码，需计算并补充 padding 后解码。
    """
    result = service.users().messages().attachments().get(
        userId='me', messageId=msg_id, id=att_id
    ).execute()
    data = result['data']
    pad = 4 - len(data) % 4
    if pad != 4:
        data += '=' * pad
    return base64.urlsafe_b64decode(data)
