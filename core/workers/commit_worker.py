# -*- coding: utf-8 -*-
"""
core/workers/commit_worker.py
后台线程，用于执行版本提交。
"""

import logging
import traceback
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class CommitWorker(QThread):
    """后台线程执行选择性提交。"""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, root_path: str, db_path: str, staged: list[str],
                 name: str, summary: str, detail: str, author: str) -> None:
        super().__init__()
        self._root_path = root_path
        self._db_path = db_path
        self._staged = staged
        self._name = name
        self._summary = summary
        self._detail = detail
        self._author = author

    def run(self) -> None:
        logger.info("Starting background commit: name='%s'", self._name)
        try:
            from db.connection import DatabaseConnection
            from core.snapshot import SnapshotService
            conn = DatabaseConnection(self._db_path)
            svc = SnapshotService(self._root_path, 1, conn)
            # 使用选择性提交：staged 列表
            res = svc.commit(
                name=self._name,
                summary=self._summary,
                detail=self._detail,
                author=self._author,
                selected_paths=self._staged,
                progress_cb=lambda c, t: self.progress.emit(c, t),
            )
            conn.commit()
            conn.close()
            logger.info("Background commit finished successfully.")
            self.finished.emit(res.snapshot_id)
        except Exception:
            logger.exception("Background commit failed.")
            self.error.emit(traceback.format_exc())
