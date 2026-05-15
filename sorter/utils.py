"""
工具函数模块：路径解析、文件名清理、重名处理
"""
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """
    获取项目根目录，兼容开发模式与 PyInstaller --onefile 打包模式。
    打包后返回可执行文件所在目录；开发时返回项目根目录（sorter/ 的上一级）。
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def sanitize_filename(name: str) -> str:
    """
    清理文件名中的非法字符，兼容 Windows 和 macOS。
    将 \\/:*?"<>| 及控制字符替换为下划线，去除首尾空格和点。
    """
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', name)
    name = name.strip('. ')
    if len(name) > 100:
        name = name[:100].rstrip()
    return name or 'unnamed'


def get_unique_filepath(directory: Path, stem: str, suffix: str) -> Path:
    """
    生成不重复的文件路径。
    若 stem+suffix 已存在，则依次尝试 stem(1)+suffix、stem(2)+suffix ...
    """
    target = directory / f"{stem}{suffix}"
    if not target.exists():
        return target
    counter = 1
    while True:
        target = directory / f"{stem}({counter}){suffix}"
        if not target.exists():
            return target
        counter += 1
