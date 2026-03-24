# -*- coding: utf-8 -*-
"""
core/workers/scan_worker.py
后台线程，用于执行工作区文件扫描。
"""

from PyQt6.QtCore import QThread, pyqtSignal
from core.working_tree import WorkingTreeScanner


class ScanWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, scanner: WorkingTreeScanner) -> None:
        super().__init__()
        self._scanner = scanner

    def run(self) -> None:
        self.done.emit(self._scanner.scan())
