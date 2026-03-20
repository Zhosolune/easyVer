# -*- coding: utf-8 -*-
"""
utils/datetime_utils.py
时间格式化工具。
"""

import time
from datetime import datetime


def ts_to_str(timestamp: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Unix 时间戳（秒）转本地时间字符串。"""
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def ts_to_relative(timestamp: int) -> str:
    """
    将时间戳转换为相对时间描述，如 '3 分钟前'、'2 天前'。
    """
    diff = int(time.time()) - timestamp
    if diff < 60:
        return "刚刚"
    if diff < 3600:
        return f"{diff // 60} 分钟前"
    if diff < 86400:
        return f"{diff // 3600} 小时前"
    if diff < 86400 * 30:
        return f"{diff // 86400} 天前"
    if diff < 86400 * 365:
        return f"{diff // (86400 * 30)} 个月前"
    return f"{diff // (86400 * 365)} 年前"


def now_ts() -> int:
    """返回当前 Unix 时间戳（秒）。"""
    return int(time.time())
