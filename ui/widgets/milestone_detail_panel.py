# -*- coding: utf-8 -*-
"""
v2/ui/widgets/milestone_detail_panel.py
右栏：里程碑详情与操作（点击卡片后显示）。
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem, QStackedWidget, QTreeWidgetItem
)
from qfluentwidgets import (
    ScrollArea, BodyLabel, StrongBodyLabel, CaptionLabel, FluentIcon,
    InfoBar, CommandBar, Action, ListWidget, ToolTipFilter, ToolTipPosition,
    TreeWidget, isDarkTheme, TransparentToolButton
)

import logging
logger = logging.getLogger(__name__)

from utils.datetime_utils import ts_to_str as ts_to_absolute
from core.workers.file_load_worker import FileLoadWorker, TreeNode

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
        self._info_panel = QWidget(self._detail_widget)
        info_layout = QVBoxLayout(self._info_panel)
        info_layout.setContentsMargins(10, 0, 10, 0)
        info_layout.setSpacing(8)

        self._title = StrongBodyLabel("", self._info_panel)
        font = self._title.font()
        font.setPixelSize(20)
        self._title.setFont(font)
        
        self._hash_label = CaptionLabel("", self._info_panel)
        self._parent_label = CaptionLabel("", self._info_panel)
        self._author_label = CaptionLabel("", self._info_panel)
        self._time_label = CaptionLabel("", self._info_panel)
        
        self._summary_label = BodyLabel("", self._info_panel)
        self._summary_label.setWordWrap(True)
        self._detail_label = BodyLabel("", self._info_panel)
        self._detail_label.setWordWrap(True)

        info_layout.addWidget(self._title)
        info_layout.addWidget(self._hash_label)
        info_layout.addWidget(self._parent_label)
        info_layout.addWidget(self._author_label)
        info_layout.addWidget(self._time_label)
        info_layout.addSpacing(4)
        info_layout.addWidget(self._summary_label)
        info_layout.addWidget(self._detail_label)
        info_layout.addStretch()

        # 3. 文件变更情况 (列表 / 树视图)
        self._file_changed_panel = QWidget(self._detail_widget)
        file_layout = QVBoxLayout(self._file_changed_panel)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)

        self._file_change_header = QWidget(self._file_changed_panel)
        self._file_change_header.setFixedHeight(50)
        file_header_layout = QHBoxLayout(self._file_change_header)
        file_header_layout.setContentsMargins(10, 0, 10, 0)

        file_title = StrongBodyLabel("文件变更情况", self._file_change_header)
        
        self._list_view_btn = TransparentToolButton(FluentIcon.MENU, self._file_change_header)
        self._list_view_btn.setToolTip("列表视图")
        self._list_view_btn.setCheckable(True)
        self._list_view_btn.setChecked(True)
        self._list_view_btn.clicked.connect(lambda: self._on_view_mode_changed("list"))
        
        self._tree_view_btn = TransparentToolButton(FluentIcon.FOLDER, self._file_change_header)
        self._tree_view_btn.setToolTip("树状视图")
        self._tree_view_btn.setCheckable(True)
        self._tree_view_btn.clicked.connect(lambda: self._on_view_mode_changed("tree"))
        
        self._stats_label = BodyLabel("", self._file_change_header)
        self._stats_label.setTextFormat(Qt.TextFormat.RichText)
        
        file_header_layout.addWidget(file_title)
        file_header_layout.addWidget(self._list_view_btn)
        file_header_layout.addWidget(self._tree_view_btn)
        file_header_layout.addStretch()
        file_header_layout.addSpacing(16)
        file_header_layout.addWidget(self._stats_label)
        file_layout.addWidget(self._file_change_header)

        # QStackedWidget for List and Tree
        self._file_stack = QStackedWidget(self._file_changed_panel)
        
        self._file_list = ListWidget(self._file_stack)
        self._file_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._file_list.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self._file_list.setUniformItemSizes(True) # 优化列表性能
        
        self._file_tree = TreeWidget(self._file_stack)
        self._file_tree.setHeaderHidden(True)
        self._file_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._file_tree.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self._file_tree.setUniformRowHeights(True) # 优化树状图性能
        self._file_tree.itemExpanded.connect(self._update_tree_height)
        self._file_tree.itemCollapsed.connect(self._update_tree_height)

        self._file_stack.addWidget(self._file_list)
        self._file_stack.addWidget(self._file_tree)
        self._file_stack.setFixedHeight(300)

        file_layout.addWidget(self._file_stack)

        dl.addWidget(self._info_panel)
        dl.addWidget(self._file_changed_panel)

        layout.addWidget(self._detail_widget)
        self._detail_widget.hide()

        self.setWidget(container)
        self.setWidgetResizable(True)
        
        self._load_worker: Optional[FileLoadWorker] = None

    def _on_view_mode_changed(self, routeKey: str) -> None:
        idx = 0 if routeKey == "list" else 1
        self._file_stack.setCurrentIndex(idx)
        # 更新按钮选中状态
        is_list = (routeKey == "list")
        self._list_view_btn.setChecked(is_list)
        self._tree_view_btn.setChecked(not is_list)
        
    def _update_tree_height(self, item=None):
        pass # Optional dynamic height adjustment

    def _get_status_color(self, status: str) -> str:
        dark = isDarkTheme()
        if status == 'added':
            return "#3fb950" if dark else "#1a7f37"
        elif status == 'deleted':
            return "#f85149" if dark else "#cf222e"
        elif status == 'modified':
            return "#d29922" if dark else "#9a6700"
        return "#cccccc" if dark else "#333333"

    def _build_file_changes(self, changed_files: list, root_node: TreeNode, added: int, modified: int, deleted: int) -> None:
        # 禁用列表重绘
        self._file_list.setUpdatesEnabled(False)
        self._file_list.clear()
        
        self._file_tree.setUpdatesEnabled(False)
        self._file_tree.clear()
        
        # 更新统计标签
        c_add = self._get_status_color('added')
        c_mod = self._get_status_color('modified')
        c_del = self._get_status_color('deleted')
        
        stats_html = f'<span style="color: {c_add};">{added}</span> <span style="color: #888;">|</span> ' \
                     f'<span style="color: {c_mod};">{modified}</span> <span style="color: #888;">|</span> ' \
                     f'<span style="color: {c_del};">{deleted}</span>'
        self._stats_label.setText(stats_html)

        # 1. 列表视图
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QFont
        hint_size = QSize(0, 24)
        for f in changed_files:
            item = QListWidgetItem(f.file_path)
            item.setSizeHint(hint_size)
            item.setToolTip(f.file_path)
            
            color = self._get_status_color(f.status)
            item.setForeground(QColor(color))
            
            if f.status == 'deleted':
                font = item.font()
                font.setStrikeOut(True)
                item.setFont(font)
                
            self._file_list.addItem(item)
            
        # 使用 Fluent Tooltip 增强列表视图
        self._file_list.setToolTipDuration(0) # 禁用原生 tooltip
        self._file_list.installEventFilter(ToolTipFilter(self._file_list, showDelay=300, position=ToolTipPosition.TOP))
        
        self._file_list.setUpdatesEnabled(True)

        # 2. 树状视图
        def build_tree_ui(parent_widget, node: TreeNode):
            # 先处理子文件夹
            for folder_name, child_node in sorted(node.children.items(), key=lambda x: x[0]):
                item = QTreeWidgetItem(parent_widget, [folder_name])
                item.setToolTip(0, folder_name)
                
                # 决定文件夹颜色
                if child_node.added_count == child_node.all_files_count:
                    f_color = self._get_status_color('added')
                    is_del = False
                elif child_node.deleted_count == child_node.all_files_count:
                    f_color = self._get_status_color('deleted')
                    is_del = True
                else:
                    f_color = self._get_status_color('modified')
                    is_del = False
                
                item.setForeground(0, QColor(f_color))
                if is_del:
                    font = item.font(0)
                    font.setStrikeOut(True)
                    item.setFont(0, font)
                
                build_tree_ui(item, child_node)
                
                if child_node.all_files_count <= 10:
                    item.setExpanded(True)
            
            # 再处理文件
            for f in sorted(node.files, key=lambda x: x.file_name):
                item = QTreeWidgetItem(parent_widget, [f.file_name])
                item.setToolTip(0, f.file_name)
                
                f_color = self._get_status_color(f.status)
                item.setForeground(0, QColor(f_color))
                
                if f.status == 'deleted':
                    font = item.font(0)
                    font.setStrikeOut(True)
                    item.setFont(0, font)

        build_tree_ui(self._file_tree, root_node)
        
        # 使用 Fluent Tooltip 增强树状视图
        self._file_tree.setToolTipDuration(0) # 禁用原生 tooltip
        self._file_tree.installEventFilter(ToolTipFilter(self._file_tree, showDelay=300, position=ToolTipPosition.TOP))
        
        self._file_tree.setUpdatesEnabled(True)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def load_milestone(self, snap_id: int) -> None:
        """加载指定里程碑的详情。"""
        if self._current_snap_id == snap_id:
            return
            
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
        self._hash_label.setText(f"哈希：#{snap.hash_id}")
        
        parent_text = f"#{snap.parent_id}" if snap.parent_id else "无 (初始版本)"
        self._parent_label.setText(f"父版本：{parent_text}")
        
        self._author_label.setText(f"作者：{snap.author}")
        self._time_label.setText(f"时间：{ts_to_absolute(snap.created_at)}")
        
        self._summary_label.setText(f"摘要：{snap.summary or '(无)'}")
        self._detail_label.setText(f"详情：{snap.detail or '(无)'}")
        self._detail_label.setVisible(bool(snap.detail))

        # 只有最新里程碑可删除
        is_latest = all_snaps[0].id == snap_id if all_snaps else False
        self.deleteAction.setEnabled(is_latest)
        self.deleteAction.setToolTip("" if is_latest else "只允许删除最新里程碑")

        self._empty_label.hide()
        self._detail_widget.show()

        # 将耗时的文件查询与树节点构建放到后台线程
        if self._load_worker is not None and self._load_worker.isRunning():
            self._load_worker.disconnect()
            self._load_worker.quit()
            self._load_worker.wait()
            
        self._load_worker = FileLoadWorker(self._root_path, snap_id, self)
        self._load_worker.finished.connect(self._build_file_changes)
        self._load_worker.start()

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
