# -*- coding: utf-8 -*-
"""
v2/ui/widgets/milestone_list_panel.py
中栏：里程碑卡片列表（时间线）。
点击卡片发出 milestone_selected(snap_id: int) 信号。
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout
)
from qfluentwidgets import (
    ScrollArea, BodyLabel, 
)

import logging
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.application import EasyVerApp

from ui.widgets.milestone_tool_bar import MilestoneToolBar
from ui.widgets.milestone_card import MilestoneCard
from ui.dialogs.tag_filter_dialog import TagFilterDialog

class MilestoneListPanel(QWidget):
    """中栏：显示里程碑列表（最新在上）。"""

    milestone_selected = pyqtSignal(int)   # snap_id

    def __init__(
        self, app: EasyVerApp, root_path: str, parent: QWidget = None
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._root_path = root_path
        self._cards: list[MilestoneCard] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        # 工具栏
        self._toolbar = MilestoneToolBar(self)
        self._toolbar.searchChanged.connect(self._on_search)
        self._toolbar.filterChanged.connect(self._on_filter)
        
        # 连接开始/结束日期选择器变更信号
        self._toolbar.startDatePicker.dateChanged.connect(self._on_date_changed)
        self._toolbar.endDatePicker.dateChanged.connect(self._on_date_changed)
        
        layout.addWidget(self._toolbar)

        # 可滚动的卡片容器
        self._scroll = ScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("milestoneListScroll")

        self._container = QWidget(self._scroll)
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setSpacing(8)
        self._card_layout.setContentsMargins(4, 4, 4, 4)
        self._card_layout.addStretch(1)

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, stretch=1)

        # 空状态提示
        self._empty_label = BodyLabel("暂无里程碑\n点击「创建里程碑」开始记录版本", self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label, stretch=1)
        self._empty_label.hide()
        
        # 搜索无结果提示
        self._no_match_label = BodyLabel("未找到匹配项", self)
        self._no_match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._no_match_label)
        layout.addStretch(1)
        self._no_match_label.hide()

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """重新从 DB 加载里程碑列表。"""
        conn = self._app.get_conn(self._root_path)
        if conn is None:
            return

        from db.repositories.snapshot_dao import SnapshotDAO
        from db.repositories.file_dao import SnapshotFileDAO
        from db.repositories.tag_dao import TagDAO

        snaps = SnapshotDAO(conn).list_by_repo(1)   # repo-level id=1
        file_dao = SnapshotFileDAO(conn)
        tag_dao = TagDAO(conn)
        
        # 一次性查询所有标签（避免 N 次查询）
        all_tags = tag_dao.list_by_repo(1)
        tags_by_snap = {}
        for t in all_tags:
            tags_by_snap.setdefault(t.snapshot_id, []).append(t)

        # 一次性查询所有快照的文件数（避免 N 次查询）
        file_counts = file_dao.count_by_repo_snapshot(1)

        # 清空旧卡片，批量禁止重绘
        self._container.setUpdatesEnabled(False)
        try:
            for card in self._cards:
                self._card_layout.removeWidget(card)
                card.deleteLater()
            self._cards.clear()

            if not snaps:
                self._container.setUpdatesEnabled(True)
                self._empty_label.show()
                self._scroll.hide()
                return

            self._empty_label.hide()
            self._scroll.show()

            # 最新在上
            for idx, snap in enumerate(snaps):
                version = len(snaps) - idx   # 最新 = 最大版本号
                file_count = file_counts.get(snap.id, 0)
                card = MilestoneCard(
                    snap.id, version, snap.name, snap.summary, snap.created_at, file_count,
                    tags_by_snap.get(snap.id, []), snap.hash_id, self._container
                )
                card.clicked_signal.connect(self._on_card_clicked)
                card.delete_tag_signal.connect(self._on_delete_tag)
                self._cards.append(card)
                # 插入到 stretch 前面
                self._card_layout.insertWidget(self._card_layout.count() - 1, card)
        finally:
            self._container.setUpdatesEnabled(True)

    def _on_card_clicked(self, snap_id: int) -> None:
        """处理卡片点击，更新选中状态并向外发出信号。

        Args:
            snap_id: 被点击卡片的快照 ID
        """
        self._select_card(snap_id)
        self.milestone_selected.emit(snap_id)

    def _select_card(self, snap_id: int) -> None:
        """将指定 snap_id 对应的卡片置为选中，其余卡片取消选中。

        Args:
            snap_id: 要选中的快照 ID；传入 -1 表示取消所有选中
        """
        for card in self._cards:
            card.setSelected(card._snap_id == snap_id)

    def _on_search(self, text: str) -> None:
        """根据搜索文本过滤卡片。"""
        text = text.strip().lower()
        has_visible = False
        for card in self._cards:
            visible = card.match_search(text)
            card.setVisible(visible)
            if visible:
                has_visible = True
        
        self._empty_label.setVisible(not has_visible and not text) # 仅在无数据且无搜索时显示“暂无里程碑”
        self._no_match_label.setVisible(not has_visible and bool(text)) # 搜索无结果显示“未找到匹配项”
        
    def _on_filter(self, filter_type: str) -> None:
        """处理筛选逻辑。"""
        logger.info("Filter selected: %s", filter_type)
        if filter_type == 'all':
            self._toolbar.reset_filters()
            self._apply_filter() # 重置后全显
            
        elif filter_type == 'date':
            self._toolbar.show_date_picker()
            # 默认不过滤，等用户选日期
            self._apply_filter(date_mode=True)
            
        elif filter_type == 'tag':
            self._open_tag_dialog()
            
        elif filter_type == 'tag_refresh':
            # Chip 删除后的刷新
            self._apply_filter(tag_mode=True)

    def _on_date_changed(self, _date: QDate):
        """开始或结束日期变化时重新过滤。"""
        self._apply_filter(date_mode=True)

    def _open_tag_dialog(self):
        """打开标签多选弹窗，让用户选择要筛选的标签。"""
        conn = self._app.get_conn(self._root_path)
        if not conn:
            return
        from db.repositories.tag_dao import TagDAO
        tags = TagDAO(conn).list_by_repo(1)
        
        # 去重：不同里程碑可能有同名标签，筛选面板只需要展示一次
        unique_tags = []
        seen_names = set()
        for t in tags:
            if t.name not in seen_names:
                seen_names.add(t.name)
                unique_tags.append(t)

        dlg = TagFilterDialog(unique_tags, self.window())
        dlg.set_selected_tags(self._toolbar.selected_tags)
        
        if dlg.exec():
            selected = dlg.get_selected_tags()
            if selected:
                self._toolbar.show_tag_filter()
                for tag_id, tag_name, tag_color in selected:
                    self._toolbar.add_tag_chip(tag_id, tag_name, tag_color)
                self._apply_filter(tag_mode=True)
            else:
                self._toolbar.reset_filters()
                self._apply_filter()

    def _apply_filter(self, date_mode=False, tag_mode=False):
        """统一应用过滤规则。

        日期范围：开始日期当天 00:00:00 ≤ created_at ≤ 结束日期当天 23:59:59。
        任意一端未选则不施加该端限制（开放区间）。
        """
        from PyQt6.QtCore import QDate, QDateTime

        has_visible = False

        # 计算日期范围的 Unix 时间戳边界
        start_ts: int | None = None
        end_ts: int | None = None
        if date_mode:
            start_date: QDate = self._toolbar.startDatePicker.date
            end_date: QDate = self._toolbar.endDatePicker.date
            
            # 使用 QTime 构建完整的 QDateTime
            from PyQt6.QtCore import QTime, Qt
            
            if start_date and start_date.isValid():
                dt_start = QDateTime(start_date, QTime(0, 0, 0), Qt.TimeSpec.LocalTime)
                start_ts = dt_start.toSecsSinceEpoch()
                
            if end_date and end_date.isValid():
                dt_end = QDateTime(end_date, QTime(23, 59, 59), Qt.TimeSpec.LocalTime)
                end_ts = dt_end.toSecsSinceEpoch()

        target_tags = self._toolbar.selected_tags if tag_mode else None

        for card in self._cards:
            visible = True

            # 日期过滤
            if date_mode and (start_ts is not None or end_ts is not None):
                ts = card._created_at
                if start_ts is not None and ts < start_ts:
                    visible = False
                if end_ts is not None and ts > end_ts:
                    visible = False

            # 标签过滤（AND 逻辑：必须包含所有选中标签）
            if tag_mode and target_tags:
                card_tag_names = {t.name for t in card._tags}
                if not target_tags.issubset(card_tag_names):
                    visible = False

            card.setVisible(visible)
            if visible:
                has_visible = True

        is_filtering = (
            (date_mode and (start_ts is not None or end_ts is not None))
            or (tag_mode and bool(target_tags))
        )
        self._empty_label.setVisible(not has_visible and not is_filtering)
        self._no_match_label.setVisible(not has_visible and is_filtering)

    def _on_delete_tag(self, tag_id: int) -> None:
        """接收悬浮标签删除操作"""
        logger.info("User requested to delete tag #%d", tag_id)
        try:
            conn = self._app.get_conn(self._root_path)
            if conn is None:
                return
            from core.tag import TagService
            TagService(1, conn).delete(tag_id)
            self.refresh()
            logger.info("Tag #%d deleted successfully", tag_id)
        except Exception:
            logger.exception("Failed to delete tag #%d", tag_id)

    def select_milestone(self, snap_id: int) -> None:
        """通过程序选中指定的里程碑卡片，并确保其在视图中可见。

        Args:
            snap_id: 要选中的快照 ID
        """
        target_card = None
        for card in self._cards:
            if card._snap_id == snap_id:
                target_card = card
                break
                
        if target_card:
            # 确保目标卡片可见（处理可能被过滤掉的情况）
            if not target_card.isVisible():
                self._toolbar.reset_filters()
                self._apply_filter()

            # 更新选中态视觉
            self._select_card(snap_id)

            # 滚动到该卡片位置
            # 使用 QTimer.singleShot 确保布局更新后再滚动
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(target_card))
            
            # 发出选中信号以更新右侧详情
            self.milestone_selected.emit(snap_id)
