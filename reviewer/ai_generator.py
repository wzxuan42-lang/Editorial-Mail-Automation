"""
Gemini API 集成：生成个性化评审反馈邮件正文
未配置 API Key 或调用失败时返回 None，由调用方回退到模板
"""
import logging
import os

logger = logging.getLogger(__name__)

_MODEL_NAME = "gemini-1.5-flash"


def generate_feedback_body(title: str, comments: list[str], final: str) -> str | None:
    """
    调用 Gemini API 生成专业、温暖的评审反馈邮件正文。

    参数：
        title    - 作品名称
        comments - 评审意见列表
        final    - 最终结果（"通过" / "不通过"）

    返回：
        AI 生成的邮件正文字符串，或 None（失败时回退到模板）
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("未配置 GEMINI_API_KEY，使用模板生成邮件正文")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(_MODEL_NAME)
    except ImportError:
        logger.warning("未安装 google-generativeai，请运行 pip install google-generativeai")
        return None
    except Exception as e:
        logger.error("Gemini 初始化失败：%s", e)
        return None

    is_accepted = "通过" in final and final != "不通过"
    comments_text = "\n".join(f"- {c}" for c in comments) if comments else "（暂无具体评语）"
    outcome_hint = "通过录用" if is_accepted else "未予录用"

    prompt = f"""你是一位专业文学杂志《龙与十字星》的编辑，请为以下投稿评审结果撰写一封专业而温暖的反馈邮件正文。

作品：《{title}》
评审意见：
{comments_text}
最终结果：{outcome_hint}

撰写要求：
1. 语气专业、真诚、温暖，体现编辑对作者的尊重
2. 自然融入评审意见，不要生硬地逐条列举
3. {"通过稿件：表达祝贺，告知请在一周内将合同发回，邮件命名'合同+作者真名+作品名'" if is_accepted else "未录用稿件：给予诚恳鼓励，感谢投稿，表达期待未来合作"}
4. 正文控制在 200 字以内
5. 只输出邮件正文内容，不含称谓、署名和日期"""

    try:
        response = model.generate_content(prompt)
        body = response.text.strip()
        logger.info("Gemini 已生成邮件正文（《%s》，%d 字）", title, len(body))
        return body
    except Exception as e:
        logger.error("Gemini API 调用失败（《%s》）：%s", title, e)
        return None
