"""
邮件解析模块：解析邮件结构、提取正文与附件、识别投稿邮件、提取作品名
"""
import base64
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# 支持下载的附件格式（小写后缀）
SUPPORTED_EXTENSIONS = {'.doc', '.docx', '.pdf', '.zip', '.txt'}


def _safe_b64decode(data: str) -> str:
    """
    安全解码 base64url 字符串为 UTF-8 文本。
    自动计算并补充缺失的 padding，解码失败时返回空字符串。
    """
    try:
        pad = 4 - len(data) % 4
        if pad != 4:
            data += '=' * pad
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
    except Exception:
        return ''


def _extract_text(payload: dict) -> str:
    """
    递归从 Gmail payload 中提取纯文本正文。
    处理顺序：text/plain → text/html（去标签）→ 递归处理 multipart 子结构。
    """
    mime = payload.get('mimeType', '')

    if mime == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        return _safe_b64decode(data) if data else ''

    if mime == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            html = _safe_b64decode(data)
            return re.sub(r'<[^>]+>', ' ', html)
        return ''

    if 'multipart' in mime:
        parts = payload.get('parts', [])
        for p in parts:
            if p.get('mimeType') == 'text/plain':
                text = _extract_text(p)
                if text.strip():
                    return text
        for p in parts:
            if p.get('mimeType') == 'text/html':
                text = _extract_text(p)
                if text.strip():
                    return text
        for p in parts:
            text = _extract_text(p)
            if text.strip():
                return text

    return ''


def _collect_attachments(payload: dict) -> list:
    """
    递归从 Gmail payload 中收集所有附件信息。
    每项包含 filename、attachment_id、size（字节数）。
    """
    result = []
    filename = payload.get('filename', '')
    if filename:
        body = payload.get('body', {})
        att_id = body.get('attachmentId', '')
        if att_id:
            result.append({
                'filename': filename,
                'attachment_id': att_id,
                'size': body.get('size', 0),
            })
    for part in payload.get('parts', []):
        result.extend(_collect_attachments(part))
    return result


def parse_email(msg: dict) -> dict:
    """
    解析 Gmail API 返回的完整邮件对象。
    返回标准化字典：id、subject、sender、date、body、attachments。
    """
    payload = msg.get('payload', {})
    headers = {
        h['name'].lower(): h['value']
        for h in payload.get('headers', [])
    }
    return {
        'id': msg.get('id', ''),
        'subject': headers.get('subject', '(无主题)'),
        'sender': headers.get('from', ''),
        'date': headers.get('date', ''),
        'body': _extract_text(payload),
        'attachments': _collect_attachments(payload),
    }


def contains_keywords(text: str, keywords: list) -> bool:
    """检查文本是否包含关键词列表中的任意一项（不区分大小写）"""
    text_lower = text.lower()
    return any(kw.strip().lower() in text_lower for kw in keywords if kw.strip())


def is_submission_email(email_data: dict, keywords: list) -> bool:
    """
    判断邮件是否为投稿邮件。
    - 无关键词：所有带附件的邮件均视为投稿。
    - 有关键词：邮件标题或正文中包含任意关键词时视为投稿。
    """
    if not keywords or all(not k.strip() for k in keywords):
        return True

    subject = email_data.get('subject', '')
    body = email_data.get('body', '')
    return (
        contains_keywords(subject, keywords) or
        contains_keywords(body, keywords)
    )


def extract_work_title(email_data: dict, attachment_filename: str = '') -> str:
    """
    提取作品名，按优先级依次尝试：
    1. 邮件标题中《》内的文字
    2. 附件文件名去掉扩展名
    3. 邮件标题本身
    """
    subject = email_data.get('subject', '')

    match = re.search(r'《(.+?)》', subject)
    if match:
        return match.group(1)

    if attachment_filename:
        stem = Path(attachment_filename).stem
        if stem:
            return stem

    return subject.strip() or '未知作品'
