# -*- coding: utf-8 -*-
"""
utils/file_utils.py
文件相关工具函数：路径处理、大小格式化、MIME 类型检测。
"""

import mimetypes
from pathlib import Path


def human_readable_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的字符串，如 '1.23 MB'。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def get_mime_type(file_path: str | Path) -> str:
    """获取文件的 MIME 类型，未知时返回 'application/octet-stream'。"""
    mime, _ = mimetypes.guess_type(str(file_path))
    return mime or "application/octet-stream"


def is_text_file(file_path: str | Path) -> bool:
    """简单判断文件是否为文本类型（基于 MIME 和扩展名）。"""
    from core.diff import TEXT_EXTENSIONS
    ext = Path(file_path).suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return True
    mime = get_mime_type(file_path)
    return mime.startswith("text/")


def normalize_path_sep(path: str) -> str:
    """将路径中的所有反斜杠替换为正斜杠（用于数据库存储统一格式）。"""
    return path.replace("\\", "/")
