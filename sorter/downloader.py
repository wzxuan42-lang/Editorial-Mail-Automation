"""
附件下载模块：遍历邮件、识别投稿、下载附件、自动编号命名
"""
import logging
from pathlib import Path
from typing import Callable

from sorter.gmail_client import get_message_detail, get_attachment_data
from sorter.parser import (
    parse_email,
    is_submission_email,
    extract_work_title,
    SUPPORTED_EXTENSIONS,
)
from sorter.utils import sanitize_filename, get_unique_filepath

logger = logging.getLogger(__name__)


def process_emails(
    service,
    message_ids: list,
    keywords: list,
    download_dir: Path,
    check_cancelled: Callable[[], bool] = None,
) -> int:
    """
    遍历邮件 ID 列表，下载符合条件的附件并按编号命名保存。

    参数：
        service        - Gmail API 服务对象
        message_ids    - 搜索结果返回的邮件 ID 列表
        keywords       - 关键词过滤列表（空列表表示不过滤）
        download_dir   - 下载目标目录
        check_cancelled - 检查取消标志的回调（可选）

    返回：
        成功下载的附件数量
    """
    download_dir.mkdir(parents=True, exist_ok=True)

    counter = 1
    downloaded = 0
    total = len(message_ids)

    for idx, msg_info in enumerate(message_ids, 1):
        if idx == 1 or idx % 10 == 0 or idx == total:
            logger.info("正在检查第 %d/%d 封邮件...", idx, total)

        if check_cancelled and check_cancelled():
            logger.info("操作已取消，停止处理")
            break

        msg_id = msg_info['id']

        try:
            msg = get_message_detail(service, msg_id)
            email_data = parse_email(msg)

            if not is_submission_email(email_data, keywords):
                continue

            for att in email_data.get('attachments', []):
                if check_cancelled and check_cancelled():
                    break

                filename = att.get('filename', '')
                ext = Path(filename).suffix.lower()

                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                work_title = extract_work_title(email_data, filename)
                clean_title = sanitize_filename(work_title)

                stem = f"{counter:03d} {clean_title}"
                target_path = get_unique_filepath(download_dir, stem, ext)

                try:
                    file_bytes = get_attachment_data(service, msg_id, att['attachment_id'])
                    target_path.write_bytes(file_bytes)
                    logger.info("已下载：%s", target_path.name)
                    counter += 1
                    downloaded += 1

                except PermissionError as e:
                    logger.error("文件权限错误：%s - %s", filename, e)
                except OSError as e:
                    logger.error("文件写入失败：%s - %s", filename, e)
                except Exception as e:
                    logger.error("附件下载失败：%s - %s: %s", filename, type(e).__name__, e)

        except Exception as e:
            logger.error("邮件处理失败（ID: %s）：%s: %s", msg_id, type(e).__name__, e)

    return downloaded
