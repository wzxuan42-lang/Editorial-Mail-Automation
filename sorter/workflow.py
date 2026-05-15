"""
Sorter workflow：Gmail 认证 → 邮件搜索 → 附件下载
提供 CLI 入口，供 main.py 调用
"""
import logging
from datetime import date
from pathlib import Path

from sorter.gmail_client import get_gmail_service, build_search_query, search_messages
from sorter.downloader import process_emails

logger = logging.getLogger(__name__)


def run_sorter(
    start_date: str = None,
    end_date: str = None,
    keywords: list = None,
    download_dir: Path = None,
) -> int:
    """
    执行邮件投稿整理 workflow。

    参数：
        start_date   - 开始日期，格式 YYYY-MM-DD，默认本月第一天
        end_date     - 结束日期，格式 YYYY-MM-DD，默认今天
        keywords     - 关键词过滤列表，空列表表示不过滤
        download_dir - 附件下载目录，默认 downloads/

    返回：
        成功下载的附件数量
    """
    today = date.today()
    start_date = start_date or today.strftime('%Y-%m-01')
    end_date = end_date or today.strftime('%Y-%m-%d')
    keywords = keywords or []
    download_dir = download_dir or Path('downloads')

    logger.info("=== 邮件投稿整理 开始 ===")
    logger.info("时间范围：%s → %s", start_date, end_date)

    try:
        service = get_gmail_service()
    except FileNotFoundError as e:
        logger.error("Gmail 认证失败：%s", e)
        raise
    except Exception as e:
        logger.error("Gmail 连接异常：%s", e)
        raise

    query = build_search_query(start_date, end_date)
    logger.info("搜索条件：%s", query)

    try:
        messages = search_messages(service, query)
    except Exception as e:
        logger.error("邮件搜索失败：%s", e)
        raise

    if not messages:
        logger.info("未找到符合条件的邮件")
        return 0

    logger.info("找到 %d 封邮件", len(messages))
    if keywords:
        logger.info("关键词筛选：%s", ", ".join(keywords))
    else:
        logger.info("未设置关键词，将处理所有带附件邮件")

    count = process_emails(
        service=service,
        message_ids=messages,
        keywords=keywords,
        download_dir=download_dir,
    )

    logger.info("=== 完成！共下载 %d 个文件 ===", count)
    logger.info("保存位置：%s", download_dir.resolve())
    return count
