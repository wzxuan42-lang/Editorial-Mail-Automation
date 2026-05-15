"""
解析 reviews.xlsx，返回每篇作品的评审信息。

列名固定，允许列顺序任意变化。
"意见（通过/不通过）" 列有三个重复列名，
用 openpyxl 按位置读取表头，然后重命名以区分。
"""
import logging
from pathlib import Path

import openpyxl
import pandas as pd

logger = logging.getLogger(__name__)

_EXPECTED_HEADERS = [
    "作品编号",
    "作品名称",
    "评委1",
    "意见（通过/不通过）",   # 第一个 → opinion_1
    "评语1",
    "评委2",
    "意见（通过/不通过）",   # 第二个 → opinion_2
    "评语2",
    "评委3",
    "意见（通过/不通过）",   # 第三个 → opinion_3
    "评语3",
    "最终意见",
]

_RENAMED_HEADERS = [
    "作品编号",
    "作品名称",
    "评委1",
    "opinion_1",
    "评语1",
    "评委2",
    "opinion_2",
    "评语2",
    "评委3",
    "opinion_3",
    "评语3",
    "最终意见",
]


def _load_raw(excel_path: Path) -> pd.DataFrame:
    """用 openpyxl 读取表头，处理重复列名后返回 DataFrame。"""
    try:
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"无法打开 Excel 文件：{excel_path} — {e}") from e

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        raise ValueError(f"Excel 文件为空：{excel_path}")

    header_row = rows[0]
    if len(header_row) != len(_RENAMED_HEADERS):
        raise ValueError(
            f"列数不符：期望 {len(_RENAMED_HEADERS)} 列，实际 {len(header_row)} 列"
        )

    df = pd.DataFrame(rows[1:], columns=_RENAMED_HEADERS)
    return df


def _clean_text(value) -> str:
    """将单元格值转为干净字符串，NaN/None 返回空字符串。"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def parse_reviews(excel_path: str | Path) -> list[dict]:
    """
    解析 Excel，返回每篇作品的评审信息列表。

    每个元素为 dict：
        {
            "id":       作品编号（str）,
            "title":    作品名称,
            "comments": 非空评语列表,
            "final":    最终意见（"通过" / "不通过"）,
        }
    跳过作品名称为空或最终意见为空的行。
    """
    excel_path = Path(excel_path).expanduser()
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel 文件不存在：{excel_path}")

    df = _load_raw(excel_path)
    results = []

    for _, row in df.iterrows():
        title = _clean_text(row.get("作品名称"))
        if not title:
            continue

        work_id = _clean_text(row.get("作品编号"))
        final = _clean_text(row.get("最终意见"))

        comments = []
        for col in ("评语1", "评语2", "评语3"):
            text = _clean_text(row.get(col))
            if text:
                comments.append(text)

        if not final:
            logger.warning("作品「%s」最终意见为空，跳过", title)
            continue

        results.append({
            "id": work_id,
            "title": title,
            "comments": comments,
            "final": final,
        })
        logger.debug("已解析：%s（%s）", title, final)

    logger.info("共解析 %d 篇作品", len(results))
    return results
