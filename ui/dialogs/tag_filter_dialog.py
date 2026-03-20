# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import MessageBoxBase, StrongBodyLabel, FlowLayout

from ui.widgets.tag_badge import TagBadge

if TYPE_CHECKING:
    from db.repositories.tag_dao import TagRecord


class TagFilterDialog(MessageBoxBase):
    """标签筛选多选弹窗 (FlowLayout + Selectable TagBadge)。"""
    
    def __init__(self, tags: list['TagRecord'], parent=None):
        super().__init__(parent)
        self.titleLabel = StrongBodyLabel("筛选标签 (多选)", self.widget)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 容器 widget
        self.container = QWidget(self.widget)
        self.flowLayout = FlowLayout(self.container)
        self.flowLayout.setContentsMargins(0, 8, 0, 8)
        self.flowLayout.setHorizontalSpacing(8)
        self.flowLayout.setVerticalSpacing(8)
        
        self.badges = []
        for tag in tags:
            # is_selectable=True, is_filter_mode=False (不需要关闭按钮)
            badge = TagBadge(tag.id, tag.name, tag.color, self.container, 
                           is_filter_mode=False, is_selectable=True)
            self.flowLayout.addWidget(badge)
            self.badges.append(badge)
            
        self.viewLayout.addWidget(self.container)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(360)
        
    def set_selected_tags(self, tag_ids: set[int]):
        """根据传入的已选 ID 集合，高亮对应的 TagBadge"""
        for badge in self.badges:
            if badge.tag_id in tag_ids:
                badge.setSelected(True)
        
    def get_selected_tags(self) -> list[tuple[int, str, str]]:
        selected = []
        for badge in self.badges:
            if badge.isSelected():
                selected.append((badge.tag_id, badge.text, badge.color.name()))
        return selected
