# -*- coding: utf-8 -*-
"""
utils/icon_provider.py
文件类型图标映射：
  - 根据文件扩展名返回对应的 FluentIcon 或自定义 QIcon
  - 供 RepoTreeWidget 用于文件节点图标显示
"""

from qfluentwidgets import FluentIcon
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QStyle, QApplication


# 扩展名 → FluentIcon 映射表
_EXT_ICON_MAP: dict[str, FluentIcon] = {
    # 代码文件
    ".py":    FluentIcon.CODE,
    ".js":    FluentIcon.CODE,
    ".ts":    FluentIcon.CODE,
    ".java":  FluentIcon.CODE,
    ".cpp":   FluentIcon.CODE,
    ".c":     FluentIcon.CODE,
    ".cs":    FluentIcon.CODE,
    ".go":    FluentIcon.CODE,
    ".rs":    FluentIcon.CODE,
    ".rb":    FluentIcon.CODE,
    ".php":   FluentIcon.CODE,
    ".sh":    FluentIcon.CODE,
    ".bat":   FluentIcon.CODE,
    ".ps1":   FluentIcon.CODE,

    # 文档
    ".md":    FluentIcon.DOCUMENT,
    ".txt":   FluentIcon.DOCUMENT,
    ".pdf":   FluentIcon.DOCUMENT,
    ".docx":  FluentIcon.DOCUMENT,
    ".doc":   FluentIcon.DOCUMENT,
    ".xlsx":  FluentIcon.DOCUMENT,
    ".xls":   FluentIcon.DOCUMENT,
    ".pptx":  FluentIcon.DOCUMENT,

    # 配置 / 数据
    ".json":  FluentIcon.SETTING,
    ".yaml":  FluentIcon.SETTING,
    ".yml":   FluentIcon.SETTING,
    ".toml":  FluentIcon.SETTING,
    ".ini":   FluentIcon.SETTING,
    ".cfg":   FluentIcon.SETTING,
    ".xml":   FluentIcon.SETTING,
    ".sql":   FluentIcon.SETTING,
    ".csv":   FluentIcon.SETTING,

    # 图片
    ".png":   FluentIcon.PHOTO,
    ".jpg":   FluentIcon.PHOTO,
    ".jpeg":  FluentIcon.PHOTO,
    ".gif":   FluentIcon.PHOTO,
    ".bmp":   FluentIcon.PHOTO,
    ".svg":   FluentIcon.PHOTO,
    ".webp":  FluentIcon.PHOTO,
    ".ico":   FluentIcon.PHOTO,

    # 压缩包
    ".zip":   FluentIcon.ZIP_FOLDER,
    ".tar":   FluentIcon.ZIP_FOLDER,
    ".gz":    FluentIcon.ZIP_FOLDER,
    ".rar":   FluentIcon.ZIP_FOLDER,
    ".7z":    FluentIcon.ZIP_FOLDER,

    # 音视频
    ".mp4":   FluentIcon.VIDEO,
    ".mkv":   FluentIcon.VIDEO,
    ".avi":   FluentIcon.VIDEO,
    ".mov":   FluentIcon.VIDEO,
    ".mp3":   FluentIcon.MUSIC,
    ".wav":   FluentIcon.MUSIC,
    ".flac":  FluentIcon.MUSIC,
}

_DEFAULT_ICON = FluentIcon.DOCUMENT


def get_file_icon(file_ext: str) -> FluentIcon:
    """
    根据文件扩展名（小写含点，如 ".py"）返回对应的 FluentIcon。
    未识别的扩展名返回通用文档图标。
    """
    return _EXT_ICON_MAP.get(file_ext.lower(), _DEFAULT_ICON)


def get_folder_icon() -> FluentIcon:
    """返回文件夹图标。"""
    return FluentIcon.FOLDER
