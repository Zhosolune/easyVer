# -*- coding: utf-8 -*-
"""
ui/dialogs/tag_dialog.py
为指定的里程碑打标签。
该对话框基于 FluentWidgets 提供一致的深浅色外观。
"""

import traceback
import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLabel
from qfluentwidgets import (
    SubtitleLabel, LineEdit, CaptionLabel, InfoBar, InfoBarPosition,
    MessageBoxBase, BodyLabel,
)
from qfluentwidgets.common.style_sheet import addStyleSheet
from ui.widgets.tag_color_picker import TagColorPicker
from app.style_sheet import StyleSheet

if TYPE_CHECKING:
    from app.application import EasyVerApp

logger = logging.getLogger(__name__)


class TagDialog(MessageBoxBase):
    """
    打标签对话框。继承 MessageBoxBase 以获得标准遮罩和流畅界面风格。
    ColorPicker 组件已通过解除父级绑定解决底层事件被吞的死锁问题。
    """

    def __init__(self, app: "EasyVerApp", root_path: str, snap_id: int, parent: QWidget = None):
        # MessageBoxBase 需要计算 parent 宽高做居中阴影，不能为 None
        actual_parent = parent or getattr(app, "main_window", None)
        super().__init__(actual_parent)
        
        # 以追加方式应用 REPO_PAGE 样式（包含 errType 错误标签、颜色选择器等规则）
        # 不覆盖 Fluent 内置 DIALOG 样式（centerWidget 背景、cancelButton 等由 Fluent 负责）
        addStyleSheet(self, StyleSheet.REPO_PAGE)
        
        self.app = app
        self.root_path = root_path
        self.snap_id = snap_id

        self.widget.setObjectName("centerWidget")
        self.titleLabel = SubtitleLabel("为里程碑打标签", self.widget)
        
        self.nameLineEdit = LineEdit(self.widget)
        self.nameLineEdit.setPlaceholderText("输入标签名 (例如: v1.0.0)")
        self.nameLineEdit.setClearButtonEnabled(True)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(BodyLabel("标签颜色：", self.widget))
        self.colorPicker = TagColorPicker(QColor("#5B9BD5"), self.widget)
        color_layout.addWidget(self.colorPicker)
        color_layout.addStretch()

        self.errorLabel = CaptionLabel("", self.widget)
        self.errorLabel.setProperty("errType", "error")
        self.errorLabel.hide()

        self.viewLayout.setSpacing(12)
        # 顶部内容边距，左右由基类控制
        self.viewLayout.setContentsMargins(24, 24, 24, 12)
        
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(4)
        self.viewLayout.addWidget(self.nameLineEdit)
        self.viewLayout.addLayout(color_layout)
        self.viewLayout.addWidget(self.errorLabel)

        self.widget.setMinimumWidth(360)
        self.hideYesButton()
        self.hideCancelButton()
        
        self.yesButton.setText("确定")
        self.yesButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.yesButton.clicked.connect(self.accept_action)
        self.yesButton.show()

        self.cancelButton.setText("取消")
        self.cancelButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancelButton.clicked.connect(self.reject)
        self.cancelButton.show()

    def validate(self) -> bool:
        """验证输入是否合法"""
        tag_name = self.nameLineEdit.text().strip()
        if not tag_name:
            self.errorLabel.setText("标签名不能为空")
            self.errorLabel.show()
            return False

        try:
            conn = self.app.get_conn(self.root_path)
            from db.repositories.tag_dao import TagDAO
            tag_dao = TagDAO(conn)
            
            # 限制总标签数
            snapshot_tags = tag_dao.list_by_snapshot(self.snap_id)
            if len(snapshot_tags) >= 5:
                self.errorLabel.setText("当前里程碑最多只允许打 5 个标签")
                self.errorLabel.show()
                return False
                
            # 使用 list_by_repo(1) 检查标签名是否冲突
            existing_tags = tag_dao.list_by_repo(1)
            for t in existing_tags:
                if t.name == tag_name:
                    self.errorLabel.setText("该标签名已存在，请换一个名称")
                    self.errorLabel.show()
                    return False

            self.errorLabel.hide()
            return True
        except Exception as e:
            self.errorLabel.setText(f"发生错误: {e}")
            self.errorLabel.show()
            return False

    def accept_action(self):
        """点击确定按钮的槽函数"""
        if not self.validate():
            return
            
        tag_name = self.nameLineEdit.text().strip()
        color_hex = self.colorPicker.color.name()
        try:
            conn = self.app.get_conn(self.root_path)
            from core.tag import TagService
            
            # 为当前快照打标签，这里 repo_id=1
            svc = TagService(1, conn)
            svc.create(
                snapshot_id=self.snap_id,
                name=tag_name,
                color=color_hex,
            )
            
            # 由于 MessageBoxBase 会处理 accept() 对应的窗体动画退出，通过基类完成
            self.accept()
            
            InfoBar.success(
                title="打标成功",
                content=f"已成功添加标签 [{tag_name}]",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window()
            )
        except Exception as e:
            logger.exception("Failed to create tag: %s", tag_name)
            self.errorLabel.setText(f"保存时出错: {e}")
            self.errorLabel.show()
