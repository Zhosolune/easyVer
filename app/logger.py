# -*- coding: utf-8 -*-
"""
app/logger.py
全软件统一的完备日志配置模块。
"""

import os
import sys
import logging
from pathlib import Path
from app.app_config import cfg

def setup_logging(log_level: int = logging.INFO) -> None:
    """
    配置全局日志系统。
    支持：
    1. 控制台带颜色高亮输出 (如果有第三方颜色库更好，这里用标准输出)。
    2. 按天滚动的日志文件，保存在 ~/.easyver/logs 目录下。

    :param log_level: 最低日志级别，默认 INFO
    """
    # 确定日志存储目录
    log_dir = Path(cfg.logDir.value).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    
    import datetime
    start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"easyver_run_{start_time}.log"

    # 日志格式
    # 根据用户要求包含: 日期, 时间, 级别, 层级/功能模块名, 文件名:行数, 信息
    log_format = "%(asctime)s | %(levelname)-8s | [%(name)s] %(filename)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(log_format, datefmt=date_format)

    # 1. 配置控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    try:
        import colorlog
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | [%(name)s] %(filename)s:%(lineno)d | %(message)s",
            datefmt=date_format,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(color_formatter)
    except ImportError:
        console_handler.setFormatter(formatter)

    try:
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
    except Exception as e:
        print(f"Warning: Failed to create log file handler: {e}")
        file_handler = None

    # 获取根日志记录器并清空全部旧有处理器（如果被重复执行）
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 将两个处理器挂载到根上
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    # 我们配置一下根后，发送一条启动信息测试
    logging.info("EasyVer global logging system initialized. Logs will be saved to: %s", log_dir)

def clear_all_logs() -> int:
    """
    清理配置目录下的所有日志文件。
    :return: 成功清理的日志文件数量
    """
    import glob
    log_dir = cfg.logDir.value
    if not os.path.exists(log_dir):
        return 0
        
    count = 0
    for log_file in glob.glob(os.path.join(log_dir, "easyver_run_*.log")):
        try:
            os.remove(log_file)
            count += 1
        except Exception as e:
            logging.error("Failed to delete %s: %s", log_file, e)
    return count
