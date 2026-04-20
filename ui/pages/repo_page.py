# -*- coding: utf-8 -*-
"""
ui/pages/repo_page.py
单仓库页面：
  左侧（可拖动）：WorkingTreePanel 文件树
  右侧：
    Header   — 仓库名 + 「创建里程碑」
    Breadcrumb — 面包屑导航（随文件树选中更新）
    Content  — 两栏（里程碑列表 卡片 | 里程碑详情 卡片）
    Footer   — 状态栏
"""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame,
)
from qfluentwidgets import (
    SubtitleLabel, PrimaryPushButton, CaptionLabel,
    FluentIcon, InfoBar, InfoBarPosition,
)

import logging
logger = logging.getLogger(__name__)

from ui.widgets.working_tree_panel import WorkingTreePanel
from ui.widgets.milestone_list_panel import MilestoneListPanel
from ui.widgets.milestone_detail_panel import MilestoneDetailPanel
from app.style_sheet import StyleSheet

if TYPE_CHECKING:
    from app.application import EasyVerApp

class RepoPage(QWidget):
    def __init__(
        self, app_instance: "EasyVerApp", root_path: str, parent: QWidget = None
    ) -> None:
        super().__init__(parent)
        self._app = app_instance
        self._root_path = root_path
        self._root_name = Path(root_path).resolve().name
        self._setup_ui()
        self._connect_signals()

        StyleSheet.REPO_PAGE.apply(self)

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def cleanup(self) -> None:
        """清理资源。"""
        if hasattr(self, '_working_tree'):
            self._working_tree.cleanup()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶层水平 Splitter（左右可拖动）
        h_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        h_splitter.setChildrenCollapsible(False)
        h_splitter.setHandleWidth(1)
        h_splitter.setObjectName("repoSplitter")

        # ── 左侧：文件树 ───────────────────────────────
        self._working_tree = WorkingTreePanel(self._app, self._root_path, self)
        self._working_tree.setObjectName("repoWorkingTree")
        h_splitter.addWidget(self._working_tree)

        # ── 右侧：header + breadcrumb + content + footer ──
        right = QWidget(self)
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)

        right_v.addWidget(self._build_header())
        right_v.addWidget(self._build_separator())
        right_v.addWidget(self._build_content(), stretch=1)
        right_v.addWidget(self._build_separator())
        right_v.addWidget(self._build_footer())

        h_splitter.addWidget(right)
        h_splitter.setSizes([360, 1000])
        outer.addWidget(h_splitter)

    def _build_separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setObjectName("repoSeparator")
        return line

    def _build_header(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(52)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 8, 16, 8)

        # record = self._app.get_record(self._root_path)
        # name = record.name if record else self._root_name
        self._title_label = SubtitleLabel("里程碑管理", bar)
        self._title_label.setObjectName("repoTitleLabel")
        self._btn_milestone = PrimaryPushButton(FluentIcon.ADD, "  创建里程碑", bar)
        self._btn_milestone.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_milestone.setFixedHeight(36)
        self._btn_milestone.clicked.connect(self._on_create_milestone)

        h.addWidget(self._title_label)
        h.addStretch()
        h.addWidget(self._btn_milestone)
        return bar

    def _build_content(self) -> QWidget:
        """双栏卡片：里程碑列表 | 里程碑详情。"""
        container = QWidget(self)
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 8, 0, 8)
        h.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal, container)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setObjectName("repoContentSplitter")

        # 里程碑列表卡片
        list_card = QFrame(container)
        list_card.setObjectName("milestoneCard")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self._milestone_list = MilestoneListPanel(self._app, self._root_path, list_card)
        list_layout.addWidget(self._milestone_list)

        # 里程碑详情卡片
        detail_card = QFrame(container)
        detail_card.setObjectName("milestoneCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        self._milestone_detail = MilestoneDetailPanel(self._app, self._root_path, detail_card)
        detail_layout.addWidget(self._milestone_detail)

        splitter.addWidget(list_card)
        splitter.addWidget(detail_card)
        splitter.setSizes([360, 560])
        h.addWidget(splitter)
        return container

    def _build_footer(self) -> QWidget:
        bar = QWidget(self)
        bar.setFixedHeight(24)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 2, 16, 2)
        self._status_label = CaptionLabel("", bar)
        h.addWidget(self._status_label)
        h.addStretch()
        return bar

    # ------------------------------------------------------------------
    # 信号连接
    # ------------------------------------------------------------------
    def _connect_signals(self) -> None:
        self._milestone_list.milestone_selected.connect(self._milestone_detail.load_milestone)
        self._milestone_detail.navigate_to_milestone.connect(self._milestone_list.select_milestone)
        self._milestone_detail.milestone_deleted.connect(self._working_tree.refresh)
        self._milestone_list.milestone_selected.connect(
            lambda sid: self._status_label.setText(f"已选中里程碑 #{sid}")
        )

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def _on_create_milestone(self) -> None:
        logger.info("User requested to create milestone in repo: %s", self._root_path)
        from ui.dialogs.create_milestone_dialog import CreateMilestoneDialog
        dlg = CreateMilestoneDialog(self._app, self._root_path, self.window())
        if dlg.exec():
            logger.info("Milestone creation dialog accepted.")
            self._refresh_all()
            InfoBar.success("里程碑创建成功", "", duration=3000,
                            position=InfoBarPosition.TOP_RIGHT, parent=self.window())

    def _refresh_all(self) -> None:
        self._working_tree.refresh()
        self._milestone_list.refresh()
        self._milestone_detail.clear()
