# -*- coding: utf-8 -*-
"""
v2/ui/widgets/milestone_detail_panel.py
右栏：里程碑详情与操作（点击卡片后显示）。
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem,
)
from qfluentwidgets import (
    ScrollArea, BodyLabel, StrongBodyLabel, CaptionLabel, FluentIcon,
    InfoBar, CommandBar, Action, ListWidget, setCustomStyleSheet,
)

import logging
logger = logging.getLogger(__name__)

from utils.datetime_utils import ts_to_str as ts_to_absolute
from utils.file_utils import human_readable_size

if TYPE_CHECKING:
    from app.application import EasyVerApp


class MilestoneDetailPanel(ScrollArea):
    """右栏：选中里程碑后显示详情和操作工具栏。"""

    def __init__(
        self, app: EasyVerApp, root_path: str, parent: QWidget = None
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._root_path = root_path
        self._current_snap_id: Optional[int] = None
        self._snap_count: int = 0   # 用于判断是否允许删除

        self._setup_ui()

    def _setup_ui(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)

        # ── 空状态 ─────────────────────────────────────────
        self._empty_label = BodyLabel("← 点击左侧里程碑卡片查看详情", self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── 详情内容（默认隐藏）──────────────────────────────
        self._detail_widget = QWidget(container)
        dl = QVBoxLayout(self._detail_widget)
        dl.setContentsMargins(4, 0, 4, 0)
        dl.setSpacing(8)

        # 1. 操作工具栏（CommandBar）
        self.commandBar = CommandBar(self._detail_widget)
        self.commandBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.restoreAction = Action(FluentIcon.HISTORY, "整体还原", self)
        self.extractAction = Action(FluentIcon.DOWNLOAD, "提取文件", self)
        self.tagAction = Action(FluentIcon.TAG, "添加标签", self)
        self.deleteAction = Action(FluentIcon.DELETE, "删除", self)

        self.restoreAction.triggered.connect(self._on_restore)
        self.extractAction.triggered.connect(self._on_extract)
        self.tagAction.triggered.connect(self._on_tag)
        self.deleteAction.triggered.connect(self._on_delete)

        self.commandBar.addAction(self.restoreAction)
        self.commandBar.addAction(self.extractAction)
        self.commandBar.addAction(self.tagAction)
        self.commandBar.addSeparator()
        self.commandBar.addAction(self.deleteAction)

        dl.addWidget(self.commandBar)

        # 2. 里程碑基本信息
        self._title = StrongBodyLabel("", self._detail_widget)
        self._version_label = CaptionLabel("", self._detail_widget)
        self._time_label = CaptionLabel("", self._detail_widget)
        self._msg_label = BodyLabel("", self._detail_widget)
        self._msg_label.setWordWrap(True)

        dl.addWidget(self._title)
        dl.addWidget(self._version_label)
        dl.addWidget(self._time_label)
        dl.addWidget(self._msg_label)
        dl.addSpacing(8)

        # 3. 文件列表
        dl.addWidget(BodyLabel("包含文件：", self._detail_widget))
        self._file_list = ListWidget(self._detail_widget)
        self._file_list.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self._file_list.setFixedHeight(220)
        dl.addWidget(self._file_list)

        layout.addWidget(self._detail_widget)
        self._detail_widget.hide()

        self.setWidget(container)
        self.setWidgetResizable(True)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def load_milestone(self, snap_id: int) -> None:
        """加载指定里程碑的详情。"""
        self._current_snap_id = snap_id
        conn = self._app.get_conn(self._root_path)
        if conn is None:
            return

        from db.repositories.snapshot_dao import SnapshotDAO
        from db.repositories.file_dao import SnapshotFileDAO

        snap_dao = SnapshotDAO(conn)
        snap = snap_dao.get_by_id(snap_id)
        if snap is None:
            return

        all_snaps = snap_dao.list_by_repo(1)
        self._snap_count = len(all_snaps)
        version = self._snap_count - next(
            (i for i, s in enumerate(all_snaps) if s.id == snap_id), 0
        )

        # 填充详情
        self._title.setText(snap.name or f"v{version}")
        self._version_label.setText(f"版本  v{version}   (#{snap.hash_id})")
        self._time_label.setText(f"时间  {ts_to_absolute(snap.created_at)}")
        
        detail_text = f"{snap.summary}\n\n{snap.detail}" if snap.detail else snap.summary
        self._msg_label.setText(detail_text or "(无说明)")

        # 文件列表
        self._file_list.clear()
        files = SnapshotFileDAO(conn).list_by_snapshot(snap_id)
        for f in files:
            status_map = {"added": "🟢", "modified": "🟠", "unchanged": "⬜", "deleted": "🔴"}
            icon = status_map.get(f.status, "•")
            item = QListWidgetItem(f"{icon}  {f.file_path}  ({human_readable_size(f.file_size)})")
            item.setData(Qt.ItemDataRole.UserRole, f.file_path)
            self._file_list.addItem(item)

        # 只有最新里程碑可删除
        is_latest = all_snaps[0].id == snap_id if all_snaps else False
        self.deleteAction.setEnabled(is_latest)
        self.deleteAction.setToolTip("" if is_latest else "只允许删除最新里程碑")

        self._empty_label.hide()
        self._detail_widget.show()

    def clear(self) -> None:
        self._current_snap_id = None
        self._detail_widget.hide()
        self._empty_label.show()

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------
    def _on_restore(self) -> None:
        if self._current_snap_id is None:
            return
        from ui.dialogs.restore_dialog import RestoreDialog
        dlg = RestoreDialog(self._app, self._root_path, self._current_snap_id, self.window())
        dlg.exec()

    def _on_extract(self) -> None:
        if self._current_snap_id is None:
            return
        from ui.dialogs.extract_dialog import ExtractDialog
        dlg = ExtractDialog(self._app, self._root_path, self._current_snap_id, self.window())
        dlg.exec()

    def _on_tag(self) -> None:
        if self._current_snap_id is None:
            return
        from ui.dialogs.tag_dialog import TagDialog
        from PyQt6.QtWidgets import QDialog
        if TagDialog(self._app, self._root_path, self._current_snap_id, self.window()).exec() == QDialog.DialogCode.Accepted:
            # 通知父页面刷新里程碑列表以展示新标签
            parent = self.parent()
            while parent and not hasattr(parent, "_milestone_list"):
                parent = parent.parent()
            if parent:
                parent._milestone_list.refresh()

    def _on_delete(self) -> None:
        if self._current_snap_id is None:
            return
        from qfluentwidgets import MessageBox
        box = MessageBox("确认删除", "此操作将删除最新里程碑记录，无法撤销。\n已存储的文件对象将在 GC 后清理。", self.window())
        if box.exec():
            logger.info("User requested to delete milestone #%d", self._current_snap_id)
            try:
                conn = self._app.get_conn(self._root_path)
                from db.repositories.snapshot_dao import SnapshotDAO
                SnapshotDAO(conn).delete(self._current_snap_id)
                logger.info("Milestone #%d deleted successfully", self._current_snap_id)
                self.clear()
                InfoBar.success("已删除里程碑", "", duration=3000, parent=self.window())
                
                # 通知父页面刷新里程碑列表
                parent = self.parent()
                while parent and not hasattr(parent, "_milestone_list"):
                    parent = parent.parent()
                if parent:
                    parent._milestone_list.refresh()
            except Exception as e:
                logger.exception("Failed to delete milestone #%d", self._current_snap_id)
                InfoBar.error("删除失败", str(e), duration=3000, parent=self.window())
