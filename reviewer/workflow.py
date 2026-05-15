"""
Reviewer workflow：解析 Excel → 搜索 Gmail → AI 生成邮件正文 → 发送反馈
提供 CLI 入口，供 main.py 调用
"""
import json
import logging
import os
import sys
from pathlib import Path

from reviewer.excel_parser import parse_reviews
from reviewer.gmail_service import get_gmail_service, search_submission_email
from reviewer.email_sender import send_feedback_email, build_email_body
from reviewer.ai_generator import generate_feedback_body

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent

# 从环境变量读取配置，未设置时使用项目根目录的默认路径
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
TOKEN_FILE = os.getenv("TOKEN_FILE", str(BASE_DIR / "token.json"))
EXCEL_FILE = os.getenv("EXCEL_FILE", str(BASE_DIR / "reviews.xlsx"))
CONTRACTS_DIR = Path(os.getenv("CONTRACTS_DIR", str(BASE_DIR / "contracts")))
SENT_LOG_FILE = Path(os.getenv("SENT_LOG_FILE", str(BASE_DIR / "sent_log.json")))
SENDER_NAME = os.getenv("SENDER_NAME", "龙与十字星编辑部")
SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "【龙与十字星】投稿评审结果通知")
CONTRACT_FILENAME = os.getenv("CONTRACT_FILENAME", "《龙与十字星》出版合同.docx")


def load_sent_log() -> set[str]:
    """返回已发送的作品标题集合，避免重复发送。"""
    if not SENT_LOG_FILE.exists():
        return set()
    try:
        data = json.loads(SENT_LOG_FILE.read_text(encoding="utf-8"))
        return set(data.get("sent", []))
    except Exception as e:
        logger.warning("读取 sent_log.json 失败：%s，将视为空记录", e)
        return set()


def save_sent_log(sent: set[str]) -> None:
    """持久化已发送记录。"""
    try:
        SENT_LOG_FILE.write_text(
            json.dumps({"sent": sorted(sent)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error("保存 sent_log.json 失败：%s", e)


def run_reviewer() -> None:
    """
    执行评审反馈 workflow：
    1. 解析 Excel 评审表
    2. Gmail OAuth 认证
    3. 逐篇搜索投稿邮件、生成正文、发送反馈
    4. 记录发送状态，避免重复
    """
    logger.info("=== 投稿反馈系统启动 ===")

    # 1. 解析 Excel
    try:
        reviews = parse_reviews(EXCEL_FILE)
    except FileNotFoundError as e:
        logger.error("Excel 文件未找到：%s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("读取 Excel 失败：%s", e)
        sys.exit(1)

    if not reviews:
        logger.info("Excel 中没有待处理的作品，退出")
        return

    # 2. Gmail 认证
    try:
        service = get_gmail_service(CREDENTIALS_FILE, TOKEN_FILE)
    except FileNotFoundError as e:
        logger.error("Gmail 凭证文件未找到：%s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Gmail 认证失败：%s", e)
        sys.exit(1)

    # 3. 加载已发送记录
    sent = load_sent_log()
    logger.info("已发送记录：%d 篇", len(sent))

    contract_path = CONTRACTS_DIR / CONTRACT_FILENAME
    success_count = 0
    skip_count = 0
    fail_count = 0

    # 4. 逐篇处理
    for review in reviews:
        title = review["title"]

        if title in sent:
            logger.info("「%s」已发送，跳过", title)
            skip_count += 1
            continue

        logger.info("处理「%s」（%s）...", title, review["final"])

        # 搜索原始投稿邮件以获取发件人
        recipient = search_submission_email(service, title)
        if not recipient:
            logger.warning("「%s」未找到投稿邮件，无法发送", title)
            fail_count += 1
            continue

        # 尝试用 Gemini 生成邮件正文，失败时回退到模板
        ai_body = generate_feedback_body(title, review["comments"], review["final"])
        if ai_body:
            logger.info("「%s」使用 AI 生成邮件正文", title)
        else:
            logger.info("「%s」使用模板生成邮件正文", title)

        ok = send_feedback_email(
            service=service,
            to=recipient,
            title=title,
            comments=review["comments"],
            final=review["final"],
            sender_name=SENDER_NAME,
            subject_prefix=SUBJECT_PREFIX,
            contract_path=contract_path,
            body=ai_body,
        )

        if ok:
            sent.add(title)
            save_sent_log(sent)
            success_count += 1
        else:
            fail_count += 1

    # 5. 汇总
    logger.info(
        "=== 完成 === 成功：%d  跳过：%d  失败：%d",
        success_count,
        skip_count,
        fail_count,
    )
