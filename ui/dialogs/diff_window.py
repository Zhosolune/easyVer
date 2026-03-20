# -*- coding: utf-8 -*-
"""
v2/ui/dialogs/diff_window.py
独立差异查看窗口（QDialog）：
  显示工作目录文件 vs 最新里程碑的行级 diff。
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTextEdit, QFrame, QWidget,
)
from qfluentwidgets import BodyLabel, CaptionLabel, StrongBodyLabel, TitleLabel

from core.diff import DiffEngine, DiffType
from db.connection import DatabaseConnection


class DiffWindow(QDialog):
    """
    独立差异查看窗口：左=最新里程碑版本，右=工作目录当前版本。
    """

    def __init__(
        self,
        root_path: str,
        conn: DatabaseConnection,
        rel_path: str,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self._root_path = Path(root_path)
        self._conn = conn
        self._rel_path = rel_path

        self.setWindowTitle(f"差异对比 — {rel_path}")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(1000, 680)
        self._setup_ui()
        self._load()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 标题栏
        header = QWidget(self)
        header.setFixedHeight(48)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 8, 16, 8)
        self._path_label = StrongBodyLabel(self._rel_path, header)
        self._summary_label = CaptionLabel("", header)
        hl.addWidget(self._path_label)
        hl.addStretch()
        hl.addWidget(self._summary_label)
        root.addWidget(header)

        line = QFrame(self); line.setFrameShape(QFrame.Shape.HLine); line.setFixedHeight(1)
        root.addWidget(line)

        # 列标题行
        col_bar = QWidget(self)
        col_bar.setFixedHeight(26)
        cl = QHBoxLayout(col_bar)
        cl.setContentsMargins(8, 2, 8, 2)
        cl.addWidget(CaptionLabel("旧版本（里程碑）", col_bar), stretch=1)
        cl.addWidget(CaptionLabel("新版本（工作目录）", col_bar), stretch=1)
        root.addWidget(col_bar)

        # 双栏 Splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        font = QFont("Consolas", 10)

        self._old_pane = QTextEdit(self)
        self._old_pane.setReadOnly(True)
        self._old_pane.setFont(font)

        self._new_pane = QTextEdit(self)
        self._new_pane.setReadOnly(True)
        self._new_pane.setFont(font)

        self._splitter.addWidget(self._old_pane)
        self._splitter.addWidget(self._new_pane)
        root.addWidget(self._splitter, stretch=1)

        # 信息/空状态标签
        self._info_label = BodyLabel("", self)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._info_label, stretch=1)
        self._info_label.hide()

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------
    def _load(self) -> None:
        old_bytes: Optional[bytes] = None
        old_sha256: Optional[str] = None

        # 获取最新里程碑版本
        from db.repositories.snapshot_dao import SnapshotDAO
        from db.repositories.file_dao import SnapshotFileDAO
        from core.storage import StorageService
        from core.repository import RepositoryService

        snaps = SnapshotDAO(self._conn).list_by_repo(1)
        if snaps:
            latest_id = snaps[0].id
            sf = SnapshotFileDAO(self._conn).get_by_path(latest_id, self._rel_path)
            if sf and sf.status != "deleted":
                objects_dir = RepositoryService.get_objects_dir(self._root_path)
                storage = StorageService(objects_dir, self._conn)
                try:
                    old_bytes = storage.read_bytes(sf.blob_sha256)
                    old_sha256 = sf.blob_sha256
                except Exception:
                    pass

        # 读取工作目录当前版本
        abs_path = self._root_path / self._rel_path
        new_bytes: Optional[bytes] = None
        if abs_path.exists():
            try:
                new_bytes = abs_path.read_bytes()
            except Exception:
                pass

        ext = Path(self._rel_path).suffix
        result = DiffEngine.diff(ext, old_bytes, new_bytes, old_sha256, None)
        self._render(result)

    def _render(self, result) -> None:
        self._summary_label.setText(result.summary)

        if result.diff_type in (
            DiffType.IDENTICAL, DiffType.BINARY,
            DiffType.TOO_LARGE, DiffType.ONLY_IN_NEW, DiffType.ONLY_IN_OLD,
        ):
            self._splitter.hide()
            self._info_label.setText(result.summary or "文件无差异")
            self._info_label.show()
            return

        self._info_label.hide()
        self._splitter.show()
        self._old_pane.clear()
        self._new_pane.clear()

        COLOR_ADD    = QColor("#1a7f37")
        COLOR_DEL    = QColor("#cf222e")
        COLOR_ADD_BG = QColor("#e6ffec")
        COLOR_DEL_BG = QColor("#ffebe9")

        old_cur = self._old_pane.textCursor()
        new_cur = self._new_pane.textCursor()

        for line in result.lines:
            fmt = QTextCharFormat()
            if line.tag == "insert":
                fmt.setBackground(COLOR_ADD_BG)
                fmt.setForeground(COLOR_ADD)
            elif line.tag == "delete":
                fmt.setBackground(COLOR_DEL_BG)
                fmt.setForeground(COLOR_DEL)

            if line.old_lineno is not None:
                old_cur.setCharFormat(fmt)
                old_cur.insertText(line.content)
            if line.new_lineno is not None:
                new_cur.setCharFormat(fmt)
                new_cur.insertText(line.content)
