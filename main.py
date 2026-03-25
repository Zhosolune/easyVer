# -*- coding: utf-8 -*-
"""
v2/main.py  —  EasyVer v2 程序入口
将父目录加入 sys.path，以便复用 core/db/utils 后端。
"""

import sys
import os
from pathlib import Path
import traceback

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QLocale, qInstallMessageHandler, QtMsgType, QMessageLogContext
from qfluentwidgets import FluentTranslator
from app.application import EasyVerApp
from app.app_config import cfg
from ui.main_window import MainWindow
from app.logger import setup_logging
from app import resource_rc
import logging

def qt_message_handler(mode: QtMsgType, context: QMessageLogContext, message: str):
    """
    拦截并处理 Qt 底层日志输出。
    主要用于屏蔽 qfluentwidgets 内部 ToolTip 读取 pixelSize 字体时导致的 -1 报错。
    """
    if "QFont::setPointSize: Point size <= 0" in message:
        return
        
    if mode == QtMsgType.QtDebugMsg:
        logging.debug(f"[Qt] {message}")
    elif mode == QtMsgType.QtInfoMsg:
        logging.info(f"[Qt] {message}")
    elif mode == QtMsgType.QtWarningMsg:
        logging.warning(f"[Qt] {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        logging.critical(f"[Qt] {message}")
    elif mode == QtMsgType.QtFatalMsg:
        logging.fatal(f"[Qt] {message}")

def exception_hook(exctype, value, tb):
    """
    Global exception hook to catch unhandled exceptions.
    Logs the full traceback and shows a critical error message box if on the main thread.
    """
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.critical("Uncaught exception:\n%s", error_msg)

    # Show error message to user only if we are in the main thread
    from PyQt6.QtCore import QThread
    if QThread.currentThread() is QApplication.instance().thread():
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Application Error")
            msg_box.setText("An unhandled exception occurred.")
            msg_box.setInformativeText(str(value))
            msg_box.setDetailedText(error_msg)
            msg_box.exec()
        except:
            pass  # If GUI fails, we at least have the log

    sys.__excepthook__(exctype, value, tb)

def main() -> None:
    setup_logging(logging.INFO)
    sys.excepthook = exception_hook
    qInstallMessageHandler(qt_message_handler)

    logging.info("=========================================")
    logging.info("EasyVer GUI Application Starting...")

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    if cfg.get(cfg.dpiScale) != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    app = QApplication(sys.argv)
    app.setApplicationName("EasyVer")
    app.setOrganizationName("EasyVer")

    # 设置组件库中文
    translator = FluentTranslator(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
    app.installTranslator(translator)

    easy_ver = EasyVerApp()

    window = MainWindow(app_instance=easy_ver)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
