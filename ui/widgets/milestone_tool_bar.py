# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (
    FluentIcon, CommandBar, Action,
    TransparentDropDownPushButton, RoundMenu, SearchLineEdit,
    setFont, FastCalendarPicker, FlowLayout
)

from ui.widgets.tag_badge import TagBadge

if TYPE_CHECKING:
    pass

class MilestoneToolBar(QWidget):
    """里程碑工具栏：包含筛选和搜索功能。"""
    searchChanged = pyqtSignal(str)
    filterChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(4, 0, 4, 0)
        self.v_layout.setSpacing(4)
        
        self.selected_tags: set[str] = set() # 存储 tag 的 name

        # 1. CommandBar
        self.commandBar = CommandBar(self)
        self.commandBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.v_layout.addWidget(self.commandBar)

        # 搜索按钮 (Toggle)
        self.searchAction = Action(FluentIcon.SEARCH, '搜索', self)
        self.searchAction.triggered.connect(self._toggle_search)
        self.commandBar.addAction(self.searchAction)

        self.commandBar.addSeparator()

        # 筛选按钮 (Custom Dropdown)
        self.filterBtn = TransparentDropDownPushButton(FluentIcon.FILTER, '筛选', self)
        self.filterBtn.setFixedHeight(34)
        setFont(self.filterBtn, 12)

        self.filterMenu = RoundMenu(parent=self)
        self.filterMenu.addActions([
            Action(FluentIcon.DATE_TIME, '按照日期', triggered=lambda: self.filterChanged.emit('date')),
            Action(FluentIcon.TAG, '按照标签', triggered=lambda: self.filterChanged.emit('tag')),
            Action(FluentIcon.CANCEL, '清除筛选', triggered=lambda: self.filterChanged.emit('all')),
        ])
        self.filterBtn.setMenu(self.filterMenu)
        self.commandBar.addWidget(self.filterBtn)

        # 2. 搜索框 (默认隐藏)
        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("搜索里程碑名称、说明等...")
        self.searchEdit.textChanged.connect(self.searchChanged)
        self.searchEdit.hide()
        self.v_layout.addWidget(self.searchEdit)

        # 3. 日期范围选择器（默认隐藏）
        self.dateRangeWidget = QWidget(self)
        date_range_layout = QHBoxLayout(self.dateRangeWidget)
        date_range_layout.setContentsMargins(4, 4, 4, 0)
        date_range_layout.setSpacing(6)

        self.startDatePicker = FastCalendarPicker(self.dateRangeWidget)
        self.startDatePicker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.startDatePicker.setText("起始时间")
        self.startDatePicker.setFixedWidth(125)
        self._date_sep = QLabel("~", self.dateRangeWidget)
        self._date_sep.setObjectName("dateRangeSep")
        self._date_sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.endDatePicker = FastCalendarPicker(self.dateRangeWidget)
        self.endDatePicker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.endDatePicker.setText("截止时间")
        self.endDatePicker.setFixedWidth(125)

        date_range_layout.addWidget(self.startDatePicker)
        date_range_layout.addWidget(self._date_sep)
        date_range_layout.addWidget(self.endDatePicker)
        date_range_layout.addStretch()
        self.dateRangeWidget.hide()
        self.v_layout.addWidget(self.dateRangeWidget)
        
        # 4. 标签筛选显示区 (默认隐藏)
        self.tagFilterWidget = QWidget(self)
        self.tagFilterLayout = FlowLayout(self.tagFilterWidget, needAni=False)
        self.tagFilterLayout.setContentsMargins(8, 4, 8, 4)
        self.tagFilterLayout.setHorizontalSpacing(4)
        self.tagFilterLayout.setVerticalSpacing(4)
        self.tagFilterWidget.hide()
        self.v_layout.addWidget(self.tagFilterWidget)

    def reset_filters(self):
        """重置所有筛选控件到初始隐藏状态。"""
        self.searchEdit.hide()
        self.searchEdit.clear()
        self.dateRangeWidget.hide()
        self.startDatePicker.setDate(QDate())
        self.startDatePicker.setText("起始时间")
        self.endDatePicker.setDate(QDate())
        self.endDatePicker.setText("截止时间")
        self.tagFilterWidget.hide()
        self.selected_tags.clear()
        
        while self.tagFilterLayout.count():
            item = self.tagFilterLayout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

    def _toggle_search(self):
        """展开/收起搜索框，收起时隐藏日期筛选和标签筛选。"""
        if self.searchEdit.isVisible():
            self.searchEdit.hide()
            self.searchEdit.clear() 
        else:
            self.dateRangeWidget.hide()
            self.tagFilterWidget.hide()
            self.searchEdit.show()
            self.searchEdit.setFocus()
            
    def show_date_picker(self):
        """显示日期范围选择器，隐藏其他筛选控件。"""
        self.searchEdit.hide()
        self.tagFilterWidget.hide()
        self.dateRangeWidget.show()
        
    def show_tag_filter(self):
        """显示标签筛选区，隐藏其他筛选控件。"""
        self.searchEdit.hide()
        self.dateRangeWidget.hide()
        self.tagFilterWidget.show()
        
    def add_tag_chip(self, tag_id: int, tag_name: str, color_hex: str = "#5B9BD5"):
        if tag_name in self.selected_tags:
            return
            
        self.selected_tags.add(tag_name)
        
        # 复用 TagBadge 作为 Chip，使用默认遮罩模式
        badge = TagBadge(tag_id, tag_name, color_hex, self.tagFilterWidget, is_filter_mode=False)
        badge.deleteClicked.connect(lambda: self.remove_tag_chip(badge))
        
        self.tagFilterLayout.addWidget(badge)

    def remove_tag_chip(self, badge: TagBadge):
        tag_name = badge.text
        if tag_name in self.selected_tags:
            self.selected_tags.remove(tag_name)
            badge.hide()
            
        self.tagFilterLayout.removeWidget(badge)
        badge.deleteLater()
        
        if not self.selected_tags:
            self.tagFilterWidget.hide()
            
        self.filterChanged.emit('tag_refresh') # 触发刷新
