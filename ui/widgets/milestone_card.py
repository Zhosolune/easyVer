# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import CardWidget, StrongBodyLabel, CaptionLabel, BodyLabel, FlowLayout

from ui.widgets.tag_badge import TagBadge
from utils.datetime_utils import ts_to_str


class MilestoneCard(CardWidget):
    """单个里程碑卡片（点击选中）。"""

    clicked_signal = pyqtSignal(int)   # snap_id
    delete_tag_signal = pyqtSignal(int) # tag_id

    def __init__(self, snap_id: int, version: int, name: str, summary: str,
                 created_at: int, file_count: int, tags: list, hash_id: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._snap_id = snap_id
        self._search_text = f"v{version} {name or ''} {summary or ''}".lower()
        self._created_at = created_at
        self._tags = tags

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui(version, name, summary, created_at, file_count, tags, hash_id)

    def match_search(self, text: str) -> bool:
        if not text:
            return True
        return text.lower() in self._search_text

    def _setup_ui(self, version: int, name: str, summary: str,
                  created_at: int, file_count: int, tags: list, hash_id: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 第一行：名称（若无名称则显示版本）+ 日期时间
        top = QHBoxLayout()
        title_text = name if name else f"v{version}"
        version_label = StrongBodyLabel(title_text, self)
        version_label.setFixedHeight(20) # 固定名称行高度
        top.addWidget(version_label)
            
        time_label = CaptionLabel(ts_to_str(created_at), self)
        time_label.setObjectName("milestoneTimeLabel")
        top.addStretch()
        top.addWidget(time_label)
        layout.addLayout(top)

        # 第二行：摘要（不带任何前缀）
        display_summary = summary if summary else "(无摘要)"
        msg_label = BodyLabel(display_summary, self)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # 第三行：哈希 + 文件数
        count_label = CaptionLabel(f"#{hash_id}   ·   包含 {file_count} 个文件", self)
        count_label.setObjectName("milestoneCountLabel")
        count_label.setFixedHeight(16) # 固定哈希行高度
        layout.addWidget(count_label)
        
        # 第四行：标签
        if not tags:
            empty_tag = CaptionLabel("标签：无", self)
            empty_tag.setObjectName("milestoneEmptyTagLabel")
            empty_tag.setFixedHeight(20) # 保持与有标签时 TagBadge 等高
            layout.addWidget(empty_tag)
        else:
            tag_flow_widget = QWidget(self)
            tag_layout = FlowLayout(tag_flow_widget, needAni=False)
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setHorizontalSpacing(4)
            tag_layout.setVerticalSpacing(4)
            for tag in tags:
                badge = TagBadge(tag.id, tag.name, tag.color, tag_flow_widget)
                badge.deleteClicked.connect(self.delete_tag_signal)
                tag_layout.addWidget(badge)
            layout.addWidget(tag_flow_widget)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.clicked_signal.emit(self._snap_id)

