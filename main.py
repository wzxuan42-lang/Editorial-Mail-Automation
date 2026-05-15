#!/usr/bin/env python3
"""
AI Journal Workflow - 统一入口

用法：
    python main.py sorter [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]
                          [--keywords kw1,kw2] [--download-dir PATH]

    python main.py reviewer
"""
import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# 从项目根目录加载 .env
load_dotenv(Path(__file__).parent / ".env")


def setup_logging() -> None:
    """配置全局日志：同时输出到终端和 logs/app.log。"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-journal-workflow",
        description="AI Journal Workflow — Gmail + Gemini 学术投稿自动化工具",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── sorter 子命令 ──────────────────────────────────────────────
    sorter_parser = subparsers.add_parser(
        "sorter",
        help="下载邮件投稿附件并自动编号归档",
    )
    sorter_parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        help="搜索起始日期（默认：本月第一天）",
    )
    sorter_parser.add_argument(
        "--end-date",
        metavar="YYYY-MM-DD",
        help="搜索结束日期（默认：今天）",
    )
    sorter_parser.add_argument(
        "--keywords",
        metavar="KW1,KW2",
        help="关键词过滤，逗号分隔（留空则处理所有带附件邮件）",
    )
    sorter_parser.add_argument(
        "--download-dir",
        metavar="PATH",
        default="downloads",
        help="附件下载目录（默认：downloads/）",
    )

    # ── reviewer 子命令 ────────────────────────────────────────────
    subparsers.add_parser(
        "reviewer",
        help="读取评审表并发送评审反馈邮件",
    )

    args = parser.parse_args()
    setup_logging()
    logger = logging.getLogger(__name__)

    if args.command == "sorter":
        keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
        download_dir = Path(args.download_dir)

        logger.info("启动 sorter workflow")
        try:
            from sorter.workflow import run_sorter
            run_sorter(
                start_date=args.start_date,
                end_date=args.end_date,
                keywords=keywords,
                download_dir=download_dir,
            )
        except Exception as e:
            logger.error("Sorter 执行失败：%s", e)
            sys.exit(1)

    elif args.command == "reviewer":
        logger.info("启动 reviewer workflow")
        try:
            from reviewer.workflow import run_reviewer
            run_reviewer()
        except Exception as e:
            logger.error("Reviewer 执行失败：%s", e)
            sys.exit(1)


if __name__ == "__main__":
    main()
