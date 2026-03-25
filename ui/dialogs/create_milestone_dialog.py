# -*- coding: utf-8 -*-
"""
v2/ui/dialogs/create_milestone_dialog.py
创建里程碑对话框：
  - 左栏：文件变更树（与最新里程碑对比），支持选择暂存
  - 右栏：已暂存文件列表
  - 底部：名称/说明输入 + 创建/取消
  - 点击文本文件 → 打开独立 DiffWindow
"""

from __future__ import annotations
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEventLoop, QSize, QEvent
from PyQt6.QtGui import QColor, QFont, QIcon, QCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidgetItem, QFrame, QStyledItemDelegate, QStyle
)
from qfluentwidgets import (
    TitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    PrimaryPushButton, PushButton, TransparentToolButton,
    TreeWidget, LineEdit, TextEdit, ProgressBar, FluentIcon,
    FluentWidget, FluentIconBase, FlowLayout
)

import logging
logger = logging.getLogger(__name__)

from core.working_tree import WorkingTreeScanner, FileStatus
from core.workers.commit_worker import CommitWorker
from utils.icon_provider import get_file_icon, get_folder_icon
from app.style_sheet import StyleSheet
from qfluentwidgets.common.style_sheet import addStyleSheet

if TYPE_CHECKING:
    from app.application import EasyVerApp


class TreeActionDelegate(QStyledItemDelegate):
    def __init__(self, tree: TreeWidget, is_staged: bool):
        super().__init__(tree)
        self.tree = tree
        self.is_staged = is_staged
        self._hovered_index = None
        tree.setMouseTracking(True)
        tree.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        try:
            viewport = self.tree.viewport()
        except RuntimeError:
            return False
            
        if obj is viewport:
            if event.type() == QEvent.Type.MouseMove:
                pos = event.pos()
                index = self.tree.indexAt(pos)
                if index.isValid() and index.column() == 2:
                    if self._hovered_index != index:
                        if self._hovered_index:
                            self.tree.viewport().update(self.tree.visualRect(self._hovered_index))
                        self._hovered_index = index
                        self.tree.viewport().update(self.tree.visualRect(self._hovered_index))
                        self.tree.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    if self._hovered_index:
                        self.tree.viewport().update(self.tree.visualRect(self._hovered_index))
                        self._hovered_index = None
                        self.tree.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            elif event.type() == QEvent.Type.Leave:
                if self._hovered_index:
                    self.tree.viewport().update(self.tree.visualRect(self._hovered_index))
                    self._hovered_index = None
                    self.tree.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(obj, event)

    def paint(self, painter, option, index):
        if index.column() != 2:
            return

        row_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if not row_hovered:
            return

        icon = FluentIcon.REMOVE if self.is_staged else FluentIcon.ADD
        is_cell_hovered = (index == self._hovered_index)

        rect = option.rect
        bg_size = 22
        icon_size = 10
        
        cx = rect.x() + rect.width() // 2
        cy = rect.y() + rect.height() // 2
        
        if is_cell_hovered:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(128, 128, 128, 50))
            painter.drawRoundedRect(cx - bg_size//2, cy - bg_size//2, bg_size, bg_size, 4, 4)
            painter.restore()

        icon.icon().paint(painter, cx - icon_size//2, cy - icon_size//2, icon_size, icon_size)


class CreateMilestoneDialog(FluentWidget):
    """创建里程碑对话框（FluentWidget 独立窗口模式）。"""

    def __init__(
        self, app: "EasyVerApp", root_path: str, parent: QWidget = None
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._root_path = root_path
        
        # 以追加方式应用 REPO_PAGE 样式（包含 errType 错误标签等规则）
        addStyleSheet(self, StyleSheet.REPO_PAGE)

        self._changed_files: list[FileStatus] = []
        self._staged: set[str] = set()
        
        # 标签状态记录
        self._preset_tags_data = [] # 数据库读出的全部预设标签 [(id, name, color)...]
        self._custom_tags_data = [] # 用户自建的自定义标签 [{"name": "", "color": ""}]
        self._selected_preset_ids = set() # 当前选中的预设标签 ID

        self.setWindowTitle("创建里程碑")
        self.resize(1000, 720)
        self.setMinimumSize(800, 500)
        
        # 1. 关闭云母特效，并使底部使用主程序的标准背景 (跟随主题)
        self.setMicaEffectEnabled(False)
        self.setCustomBackgroundColor(QColor(243, 243, 243), QColor(32, 32, 32))

        # 2. Setup UI
        self._setup_ui()
        self._load_changes()

    def exec(self) -> int:
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.show()
        self._loop = QEventLoop(self)
        self._loop.exec()
        return getattr(self, "_result", 0)

    def accept(self) -> None:
        self._result = 1
        if hasattr(self, "_loop"):
            self._loop.quit()
        self.close()

    def reject(self) -> None:
        self._result = 0
        if hasattr(self, "_loop"):
            self._loop.quit()
        self.close()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 48, 0, 0)

        # 全局左右 Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        # 隐藏自带的分隔线
        splitter.setHandleWidth(0)

        # ── 左侧：文件状态区 (上下两栏) ────────────────────────────────
        left = QWidget(self)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 8, 8, 8)
        ll.setSpacing(8)

        # 顶部工具栏 (全部暂存/刷新等)
        l_toolbar = QHBoxLayout()
        l_toolbar.addWidget(StrongBodyLabel("文件变更", left))
        l_toolbar.addStretch()
        btn_refresh = TransparentToolButton(FluentIcon.SYNC, left)
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.setToolTip("刷新")
        btn_refresh.clicked.connect(self._load_changes)
        
        btn_stage_all = TransparentToolButton(FluentIcon.ADD, left)
        btn_stage_all.setFixedSize(30, 30)
        btn_stage_all.setToolTip("全部暂存")
        btn_stage_all.clicked.connect(self._stage_all)

        btn_unstage_all = TransparentToolButton(FluentIcon.REMOVE, left)
        btn_unstage_all.setFixedSize(30, 30)
        btn_unstage_all.setToolTip("全部取消暂存")
        btn_unstage_all.clicked.connect(self._unstage_all)

        l_toolbar.addWidget(btn_refresh)
        l_toolbar.addWidget(btn_stage_all)
        l_toolbar.addWidget(btn_unstage_all)
        ll.addLayout(l_toolbar)

        # 左侧上下 Splitter
        left_splitter = QSplitter(Qt.Orientation.Vertical, left)
        left_splitter.setHandleWidth(0)

        # 1. 暂存的更改区域 (staged)
        staged_widget = QWidget(left_splitter)
        sl = QVBoxLayout(staged_widget)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(2)
        self._lbl_staged = BodyLabel("暂存的更改", staged_widget)
        sl.addWidget(self._lbl_staged)
        self._tree_staged = self._create_tree(staged_widget, is_staged=True)
        sl.addWidget(self._tree_staged, stretch=1)
        left_splitter.addWidget(staged_widget)

        # 2. 更改区域 (unstaged)
        unstaged_widget = QWidget(left_splitter)
        ul = QVBoxLayout(unstaged_widget)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.setSpacing(2)
        self._lbl_unstaged = BodyLabel("更改", unstaged_widget)
        ul.addWidget(self._lbl_unstaged)
        self._tree_unstaged = self._create_tree(unstaged_widget, is_staged=False)
        ul.addWidget(self._tree_unstaged, stretch=1)
        left_splitter.addWidget(unstaged_widget)

        left_splitter.setSizes([200, 350])
        ll.addWidget(left_splitter, stretch=1)
        splitter.addWidget(left)

        # ── 右侧：表单提交区 ──────────────────────────────────────────
        right = QWidget(self)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 8, 16, 12)
        rl.setSpacing(8)

        # 头部预留一个空 Widget / Layout 起点与左侧工具栏对齐 (通过加点Margin)
        meta_layout = QVBoxLayout()
        meta_layout.setContentsMargins(0, 4, 0, 0)
        meta_layout.setSpacing(16) # 加大行间距
        
        label_width = 75  # 略微放宽左侧表头固定宽度
        input_max_width = 450 # 放宽输入框最大宽度
        
        # 0. 里程碑名称
        name_row = QHBoxLayout()
        lbl_name = BodyLabel("名称：", right)
        lbl_name.setFixedWidth(label_width)
        name_row.addWidget(lbl_name)
        self._name_edit = LineEdit(right)
        self._name_edit.setPlaceholderText("请输入里程碑的简短名称 (必填)")
        self._name_edit.setFixedHeight(32)
        self._name_edit.setMaximumWidth(input_max_width)
        name_row.addWidget(self._name_edit)
        name_row.addStretch(1)
        meta_layout.addLayout(name_row)

        # 1. 父版本 (ReadOnly Display)
        parent_row = QHBoxLayout()
        lbl_parent = BodyLabel("父版本：", right)
        lbl_parent.setFixedWidth(label_width)
        parent_row.addWidget(lbl_parent)
        self._lbl_parent_version = BodyLabel("-", right)
        self._lbl_parent_version.setTextColor(QColor(120, 120, 120), QColor(150, 150, 150))
        parent_row.addWidget(self._lbl_parent_version)
        parent_row.addStretch(1)
        meta_layout.addLayout(parent_row)

        # 2. 作者 (LineEdit)
        author_row = QHBoxLayout()
        lbl_author = BodyLabel("作者：", right)
        lbl_author.setFixedWidth(label_width)
        author_row.addWidget(lbl_author)
        self._author_edit = LineEdit(right)
        self._author_edit.setPlaceholderText("姓名 (默认未知)")
        self._author_edit.setFixedHeight(32)
        self._author_edit.setMaximumWidth(input_max_width)
        author_row.addWidget(self._author_edit)
        author_row.addStretch(1)
        meta_layout.addLayout(author_row)

        # 3. 标签系统
        tag_vbox = QVBoxLayout()
        tag_vbox.setSpacing(8)
        
        # 3.1 预设标签流式布局 (第一行)
        tag_preset_row = QHBoxLayout()
        lbl_tags = BodyLabel("设置标签：", right)
        lbl_tags.setFixedWidth(label_width)
        tag_preset_row.addWidget(lbl_tags)
        
        self._tag_flow_widget = QWidget(right)
        self._tag_flow_layout = FlowLayout(self._tag_flow_widget, needAni=False)
        self._tag_flow_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_flow_layout.setSpacing(8)
        tag_preset_row.addWidget(self._tag_flow_widget, stretch=1)
        tag_vbox.addLayout(tag_preset_row)
        
        # 3.2 自定义新增标签 (第二行)
        tag_custom_row = QHBoxLayout()
        lbl_custom = BodyLabel("自定义：", right)
        lbl_custom.setFixedWidth(label_width)
        tag_custom_row.addWidget(lbl_custom)
        
        self._tag_name_edit = LineEdit(right)
        self._tag_name_edit.setPlaceholderText("自定义新标签名...")
        self._tag_name_edit.setFixedHeight(32)
        self._tag_name_edit.setMaximumWidth(150)
        tag_custom_row.addWidget(self._tag_name_edit)
        
        from ui.widgets.tag_color_picker import TagColorPicker
        self._tag_color_bg = TagColorPicker(QColor("#0078D4"), right)
        tag_custom_row.addWidget(self._tag_color_bg)
        
        self._btn_add_tag = PushButton("添加", right)
        self._btn_add_tag.clicked.connect(self._on_add_custom_tag)
        tag_custom_row.addWidget(self._btn_add_tag)
        tag_custom_row.addStretch(1)
        
        tag_vbox.addLayout(tag_custom_row)
        meta_layout.addLayout(tag_vbox)

        # 把上面的元数据装进主 Right 盒子
        rl.addLayout(meta_layout)
        rl.addSpacing(16)
        
        # 里程碑说明 (两段式)
        rl.addWidget(StrongBodyLabel("提交说明", right))

        self._summary_edit = LineEdit(right)
        self._summary_edit.setPlaceholderText("简短摘要 (限制 30 字，必填)，例如：发布 1.0 正式版")
        self._summary_edit.setMaxLength(30)
        self._summary_edit.setFixedHeight(32)
        rl.addWidget(self._summary_edit)

        self._msg_edit = TextEdit(right)
        self._msg_edit.setPlaceholderText("详细说明 (选填)...")
        rl.addWidget(self._msg_edit, stretch=1)

        # 进度与错误
        self._progress = ProgressBar(right)
        self._progress.setRange(0, 100)
        self._progress.hide()
        
        self._err_label = CaptionLabel("", right)
        self._err_label.setProperty("errType", "error")
        self._err_label.hide()
        
        rl.addWidget(self._progress)
        rl.addWidget(self._err_label)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self._btn_cancel = PushButton("取消", right)
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_create = PrimaryPushButton(FluentIcon.ADD, "创建", right)
        self._btn_create.clicked.connect(self._on_create)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_cancel)
        btn_layout.addWidget(self._btn_create)
        rl.addLayout(btn_layout)

        splitter.addWidget(right)
        splitter.setSizes([320, 480]) # 左窄右宽
        
        root.addWidget(splitter, stretch=1)

    def _create_tree(self, parent: QWidget, is_staged: bool) -> TreeWidget:
        tree = TreeWidget(parent)
        tree.setHeaderHidden(True)
        tree.setColumnCount(3) # 列0: 名称, 列1: 状态标记, 列2: 动作按钮(透明按键)
        tree.setIndentation(14)
        tree.setColumnWidth(0, 200)
        tree.setColumnWidth(1, 30)
        tree.setColumnWidth(2, 30)
        tree.setSelectionMode(TreeWidget.SelectionMode.SingleSelection)
        # 禁用水平滚动条，防止操作按钮被挤到外面去
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        delegate = TreeActionDelegate(tree, is_staged)
        tree.setItemDelegateForColumn(2, delegate)
        tree.setProperty("actionDelegate", delegate) # keep reference
        
        if is_staged:
            tree.itemDoubleClicked.connect(self._on_staged_dblclick)
            tree.itemClicked.connect(self._on_staged_click)
        else:
            tree.itemDoubleClicked.connect(self._on_unstaged_dblclick)
            tree.itemClicked.connect(self._on_unstaged_click)
            
        return tree

    # ------------------------------------------------------------------
    # 数据与视图核心
    # ------------------------------------------------------------------
    def _load_changes(self) -> None:
        conn = self._app.get_conn(self._root_path)
        if conn is None:
            return
            
        # 顺便获取并渲染父版本与作者默认值 (如果还未赋值的话)
        from db.repositories.snapshot_dao import SnapshotDAO
        from core.repository import RepositoryService
        from db.repositories.tag_dao import TagDAO
        
        snap_dao = SnapshotDAO(conn)
        parent_snap = snap_dao.get_latest(1)
        # 仅加载一次避免刷新覆盖用户修改
        if not self._author_edit.text():
            self._author_edit.setText(RepositoryService.current_author())
            
        # 加载所有预设系统标签
        if not hasattr(self, '_preset_tags_data') or not self._preset_tags_data:
            self._preset_tags_data = [
                {"id": 10001, "name": "重要", "color": "#E53935", "description": "核心重大的变更"},
                {"id": 10002, "name": "临时", "color": "#FB8C00", "description": "应急性的临时修复"},
                {"id": 10003, "name": "停止维护", "color": "#757575", "description": "标记废弃或停止修改"},
                {"id": 10004, "name": "配置", "color": "#3949AB", "description": "涉及配置文件改动"},
                {"id": 10005, "name": "重构", "color": "#8E24AA", "description": "架构或代码层面的重构"}
            ]
            self._refresh_tag_flow()
            
        if parent_snap:
            # 去除可能的折行符展示
            clean_msg = f"[{parent_snap.name}] {parent_snap.summary}".replace('\n', ' ')
            if len(clean_msg) > 30:
                clean_msg = clean_msg[:27] + '...'
            self._lbl_parent_version.setText(f"#{parent_snap.hash_id} - {clean_msg}")
        else:
            self._lbl_parent_version.setText("无 (当前为首次创建)")

        scanner = WorkingTreeScanner(self._root_path, conn)
        self._changed_files = scanner.get_changed()

        # 默认第一次加载全不暂存
        # 若是手动刷新，为了保存状态，我们保留 self._staged 中的有效路径
        all_paths = {fs.rel_path for fs in self._changed_files}
        self._staged.intersection_update(all_paths)
        
        # 将全部文件初始化到两棵树，后续仅作隐藏/显示，从根源上杜绝 DOM 删除导致的崩溃
        self._tree_staged.setUpdatesEnabled(False)
        self._tree_unstaged.setUpdatesEnabled(False)
        try:
            self._tree_staged.clear()
            self._tree_unstaged.clear()
            self._populate_tree(self._tree_staged, self._changed_files, is_staged=True)
            self._populate_tree(self._tree_unstaged, self._changed_files, is_staged=False)
        finally:
            self._tree_staged.setUpdatesEnabled(True)
            self._tree_unstaged.setUpdatesEnabled(True)
            
        self._update_tree_visibility()

    def _update_tree_visibility(self) -> None:
        """极速状态切换算法：绝不增删或挪移 C++ 对象，仅通过 setHidden 操作可见性。
        没有任何物理修改意味着：在点击事件执行栈中它是绝对安全的（无悬垂指针），且性能为 O(N) 属性遍历，极快。"""
        self._tree_staged.setUpdatesEnabled(False)
        self._tree_unstaged.setUpdatesEnabled(False)
        
        def apply_visibility(tree: TreeWidget, is_staged_tree: bool) -> None:
            def walk(item: QTreeWidgetItem) -> bool:
                node_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
                rel_path = item.data(0, Qt.ItemDataRole.UserRole)
                
                if node_type == "dir":
                    any_visible = False
                    for i in range(item.childCount()):
                        if walk(item.child(i)):
                            any_visible = True
                    item.setHidden(not any_visible)
                    return any_visible
                else:
                    is_staged = rel_path in self._staged
                    visible = is_staged if is_staged_tree else not is_staged
                    item.setHidden(not visible)
                    return visible

            for i in range(tree.topLevelItemCount()):
                walk(tree.topLevelItem(i))

        apply_visibility(self._tree_staged, True)
        apply_visibility(self._tree_unstaged, False)
        
        self._update_count_labels()
        
        self._tree_staged.setUpdatesEnabled(True)
        self._tree_unstaged.setUpdatesEnabled(True)

    def _populate_tree(self, tree: TreeWidget, files: list[FileStatus], is_staged: bool) -> None:
        _dir_nodes: dict[str, QTreeWidgetItem] = {}
        _dir_status: dict[str, str] = {}
        _dir_file_counts: dict[str, int] = {}

        # 统计目录文件数和综合状态
        for fs in files:
            parts = fs.rel_path.split("/")
            for i in range(1, len(parts)):
                d = "/".join(parts[:i])
                _dir_file_counts[d] = _dir_file_counts.get(d, 0) + 1
                
                current_st = _dir_status.get(d)
                if current_st is None:
                    _dir_status[d] = fs.status
                elif current_st != fs.status:
                    _dir_status[d] = "modified"

        for fs in files:
            parts = fs.rel_path.split("/")
            parent_item: Optional[QTreeWidgetItem] = None

            for depth, part in enumerate(parts[:-1]):
                key = "/".join(parts[:depth + 1])
                if key not in _dir_nodes:
                    node = QTreeWidgetItem(parent_item or tree, [part, "", ""])
                    node.setIcon(0, get_folder_icon().icon())
                    node.setData(0, Qt.ItemDataRole.UserRole, key)
                    node.setData(0, Qt.ItemDataRole.UserRole + 1, "dir")
                    
                    st = _dir_status.get(key, "modified")
                    st_char = "M"
                    color = QColor("#e36209")
                    if st == "added":
                        st_char = "N"
                        color = QColor("#1a7f37")
                    elif st == "deleted":
                        st_char = "D"
                        color = QColor("#cf222e")

                    node.setText(1, st_char)
                    node.setForeground(1, color)
                    font = node.font(1)
                    font.setBold(True)
                    node.setFont(1, font)
                    node.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    node.setToolTip(2, "全部取消暂存" if is_staged else "全部暂存")

                    _dir_nodes[key] = node
                parent_item = _dir_nodes[key]

            # 文件节点
            status_text = ""
            color = Qt.GlobalColor.black
            if fs.status == "added":
                status_text = "N"
                color = QColor("#1a7f37")
            elif fs.status == "modified":
                status_text = "M"
                color = QColor("#e36209")
            elif fs.status == "deleted":
                status_text = "D"
                color = QColor("#cf222e")

            item = QTreeWidgetItem(parent_item or tree, [parts[-1], status_text, ""])
            item.setIcon(0, get_file_icon(fs.ext).icon())
            
            # 显示状态字
            item.setForeground(1, color)
            font = item.font(1)
            font.setBold(True)
            item.setFont(1, font)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            item.setData(0, Qt.ItemDataRole.UserRole, fs.rel_path)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, fs)
            item.setToolTip(2, "取消暂存" if is_staged else "暂存")
            
        for key, node in _dir_nodes.items():
            if _dir_file_counts.get(key, 0) <= 10:
                node.setExpanded(True)
            else:
                node.setExpanded(False)

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def _on_staged_click(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 2:
            self._handle_action(item, stage=False)

    def _on_unstaged_click(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 2:
            self._handle_action(item, stage=True)

    def _handle_action(self, item: QTreeWidgetItem, stage: bool) -> None:
        node_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if node_type == "dir":
            dir_key: str = item.data(0, Qt.ItemDataRole.UserRole)
            for fs in self._changed_files:
                if fs.rel_path.startswith(dir_key + "/") or fs.rel_path == dir_key:
                    if stage:
                        self._staged.add(fs.rel_path)
                    else:
                        self._staged.discard(fs.rel_path)
        else:
            rel_path: str = item.data(0, Qt.ItemDataRole.UserRole)
            if stage:
                self._staged.add(rel_path)
            else:
                self._staged.discard(rel_path)
                
        self._update_tree_visibility()

    def _update_count_labels(self) -> None:
        staged_count = len(self._staged)
        unstaged_count = len(self._changed_files) - staged_count
        self._lbl_staged.setText(f"暂存的更改 ({staged_count})")
        self._lbl_unstaged.setText(f"更改 ({unstaged_count})")

    def _stage_all(self) -> None:
        for fs in self._changed_files:
            self._staged.add(fs.rel_path)
        self._update_tree_visibility()

    def _unstage_all(self) -> None:
        self._staged.clear()
        self._update_tree_visibility()

    def _on_staged_dblclick(self, item: QTreeWidgetItem, column: int) -> None:
        self._open_diff(item)
        
    def _on_unstaged_dblclick(self, item: QTreeWidgetItem, column: int) -> None:
        self._open_diff(item)

    def _open_diff(self, item: QTreeWidgetItem) -> None:
        fs: Optional[FileStatus] = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if fs is None:
            return
        ext = fs.ext.lower().lstrip(".")
        TEXT_EXTS = {
            "txt", "py", "js", "ts", "java", "cpp", "c", "cs", "go", "rs",
            "md", "json", "yaml", "yml", "toml", "ini", "cfg", "xml", "html",
            "css", "sh", "bat", "sql", "csv",
        }
        if ext in TEXT_EXTS:
            from ui.dialogs.diff_window import DiffWindow
            conn = self._app.get_conn(self._root_path)
            win = DiffWindow(self._root_path, conn, fs.rel_path, parent=self)
            win.show()

    # ------------------------------------------------------------------
    # 标签扩展区 (多选及自定义流)
    # ------------------------------------------------------------------
    def _refresh_tag_flow(self) -> None:
        """清空并重绘流式布局中的所有预设及自定义标签徽章"""
        while self._tag_flow_layout.count():
            item = self._tag_flow_layout.takeAt(0)
            if not item: continue
            w = item.widget() if hasattr(item, "widget") else item
            if hasattr(w, "deleteLater"):
                w.deleteLater()
        self._tag_flow_layout.removeAllWidgets()
        
        from ui.widgets.tag_badge import TagBadge
        
        # 系统预设标签（点击切换选中状态，不可删除）
        for tag in self._preset_tags_data:
            badge = TagBadge(tag["id"], tag["name"], tag["color"], self._tag_flow_widget, is_selectable=True)
            badge.setSelected(tag["id"] in self._selected_preset_ids)
            badge.toggled.connect(lambda state, tid=tag["id"]: 
                                  self._selected_preset_ids.add(tid) if state else self._selected_preset_ids.discard(tid))
            self._tag_flow_layout.addWidget(badge)
            
        # 自定义标签（默认新增不选中，且支持点击取消与悬浮删除）
        for custom in self._custom_tags_data:
            badge = TagBadge(-1, custom["name"], custom["color"], self._tag_flow_widget, is_selectable=True, is_deletable=True)
            badge.setSelected(custom.get("selected", False))
            badge.toggled.connect(lambda state, c=custom: c.update({"selected": state}))
            badge.deleteClicked.connect(lambda _, c=custom: self._remove_custom_tag(c))
            self._tag_flow_layout.addWidget(badge)

    def _on_add_custom_tag(self) -> None:
        name = self._tag_name_edit.text().strip()
        if not name:
            from qfluentwidgets import InfoBar
            InfoBar.warning("无法添加", "自定义标签名不能为空", duration=2000, parent=self)
            return
            
        # 查重
        for pt in self._preset_tags_data:
            if pt["name"] == name:
                InfoBar.warning("无法添加", "与已有标签同名", duration=2000, parent=self)
                return
        for ct in self._custom_tags_data:
            if ct["name"] == name:
                InfoBar.warning("无法添加", "该自定义标签已存在列表", duration=2000, parent=self)
                return
                
        color_hex = self._tag_color_bg.color.name().upper()
        self._custom_tags_data.append({"name": name, "color": color_hex, "selected": False})
        self._tag_name_edit.clear()
        self._refresh_tag_flow()

    def _remove_custom_tag(self, custom_dict: dict) -> None:
        if custom_dict in self._custom_tags_data:
            self._custom_tags_data.remove(custom_dict)
            self._refresh_tag_flow()

    # ------------------------------------------------------------------
    # 提交
    # ------------------------------------------------------------------
    def _on_create(self) -> None:
        milestone_name = self._name_edit.text().strip()
        summary = self._summary_edit.text().strip()
        detail = self._msg_edit.toPlainText().strip()
        
        if not milestone_name:
            self._err_label.setText("⚠ 请填写里程碑名称")
            self._err_label.show()
            return
            
        if not summary:
            self._err_label.setText("⚠ 请填写里程碑摘要")
            self._err_label.show()
            return
            
        # 废弃直接拼接，将其拆解并传入 _CommitWorker

        staged_list = list(self._staged)
        if not staged_list:
            self._err_label.setText("⚠ 请至少暂存一个文件")
            self._err_label.show()
            return
            
        author = self._author_edit.text().strip()
        if not author:
            author = "Unknown"

        self._err_label.hide()
        self._progress.show()
        self._btn_create.setEnabled(False)
        self._btn_cancel.setEnabled(False)

        from core.repository import RepositoryService
        db_path = str(RepositoryService.get_db_path(self._root_path))

        self._worker = CommitWorker(self._root_path, db_path, staged_list, milestone_name, summary, detail, author)
        self._worker.progress.connect(lambda c, t: self._progress.setValue(int(100 * c / max(t, 1))))
        self._worker.finished.connect(self._on_commit_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        
    def _on_commit_finished(self, new_snap_id: int) -> None:
        """完成创建后将勾选的已有标签及自创的全新标签打入记录"""
        try:
            conn = self._app.get_conn(self._root_path)
            from db.repositories.tag_dao import TagDAO
            tag_dao = TagDAO(conn)
            
            # 1. 保存从系统预设中选中的标签的引用
            for pt in self._preset_tags_data:
                if pt["id"] in self._selected_preset_ids:
                    tag_dao.insert(1, new_snap_id, pt["name"], pt["color"], pt["description"])
                    
            # 2. 插入自创标签 (只有保持选中态的才落库)
            for ct in self._custom_tags_data:
                if ct.get("selected", True):
                    tag_dao.insert(1, new_snap_id, ct["name"], ct["color"], "")
                
        except Exception as e:
            logger.error(f"Failed to create tag attachments: {e}")
            
        # 注意：此处需要确保关闭了连接，因为后台线程的 conn 是独立的，
        # 但我们这里是在主线程（_on_commit_finished 槽函数中）操作数据库。
        # 考虑到这里是从 self._app 获取的 persistent connection（不应该被关闭），
        # 我们只做 commit 操作。
        if 'conn' in locals():
            conn.commit()
            
        self.accept()

    def _on_error(self, tb: str) -> None:
        self._btn_create.setEnabled(True)
        self._btn_cancel.setEnabled(True)
        self._progress.hide()
        last_line = [l for l in tb.strip().splitlines() if l.strip()][-1]
        self._err_label.setText(f"❌ {last_line}")
        self._err_label.show()
        print(tb, file=sys.stderr)
