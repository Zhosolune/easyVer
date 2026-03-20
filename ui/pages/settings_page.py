# -*- coding: utf-8 -*-
"""v2/ui/pages/settings_page.py — 设置页（主题切换）。"""

from PyQt6.QtWidgets import QWidget, QFileDialog
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, OptionsSettingCard, FluentIcon,
    ExpandGroupSettingCard, InfoBar, ExpandLayout, PushButton, CustomColorSettingCard, 

)
from qfluentwidgets import qconfig, setTheme, setThemeColor
from app.app_config import cfg
from app.style_sheet import StyleSheet
from app.logger import clear_all_logs
import os
import logging

logger = logging.getLogger(__name__)


class LogSettingCard(ExpandGroupSettingCard):
    """ 日志设置卡片 """
    def __init__(self, parent=None):
        super().__init__(
            FluentIcon.DOCUMENT,
            "日志选项",
            cfg.logDir.value,
            parent
        )

        # 初始化按钮
        self.changePathBtn = PushButton("更改")
        self.openPathBtn = PushButton("打开")
        self.clearLogsBtn = PushButton("清理")
        
        self.changePathBtn.setFixedWidth(120)
        self.openPathBtn.setFixedWidth(120)
        self.clearLogsBtn.setFixedWidth(120)

        # 添加设置组
        self.logPathGroup = self.addGroup(
            FluentIcon.FOLDER,
            "自定义日志保存路径",
            "选择全量系统运行日志的统一落盘文件夹",
            self.changePathBtn
        )
        
        self.addGroup(
            FluentIcon.VIEW,
            "打开日志所在目录",
            "在文件管理器中浏览日志",
            self.openPathBtn
        )
        
        self.addGroup(
            FluentIcon.DELETE,
            "清理全部日志文件",
            "永久删除磁盘上所有当前配置目录下的日志",
            self.clearLogsBtn
        )

    def setLogPath(self, path: str):
        self.setContent(path)
        # 同时也更新内部组的显示内容（可选，如果需要同步更新内部描述）
        # self.logPathGroup.setContent(path) # 注意：GroupWidget 可能没有 setContent 方法，需检查
        # 根据文档 GroupWidget 有 setContent 方法
        # self.logPathGroup.setContent(path) 


class SettingPage(ScrollArea):
    # 内容区最大宽度（px），超出后左右边距自动增大实现居中
    MAX_CONTENT_WIDTH = 860

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.settingScrollWidget = QWidget()
        self.cardGroupsLayout = ExpandLayout(self.settingScrollWidget)

        # 外观
        self._interfaceGroup = SettingCardGroup("外观", self.settingScrollWidget)
        # 主题设置卡
        self._themeCard = OptionsSettingCard(
            cfg.themeMode,
            FluentIcon.BRUSH,
            "主题",
            "选择应用显示主题",
            texts=["浅色", "深色", "跟随系统"],
            parent=self._interfaceGroup,
        )
        # 主题色设置卡
        self._themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FluentIcon.PALETTE,
            "主题色",
            "改变应用显示的主题色",
            parent=self._interfaceGroup,
        )
        # 界面缩放设置卡
        self._zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FluentIcon.ZOOM,
            "界面缩放",
            "改变应用显示的界面缩放比例",
            texts=[
                "100%", "125%", "150%", "175%", "200%",
                "使用系统设置"
            ],
            parent=self._interfaceGroup
        )

        # 高级
        self._advancedGroup = SettingCardGroup("高级", self.settingScrollWidget)
        self._logCard = LogSettingCard(self._advancedGroup)

        self._initWidget()

    def _initWidget(self):
        # self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 28, 0, 20)
        self.setWidget(self.settingScrollWidget)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()
        self.setObjectName("settingPage")

        # 初始化样式
        self.settingScrollWidget.setObjectName('settingScrollWidget')
        # self.settingLabel.setObjectName('settingLabel')
        StyleSheet.SETTING_PAGE.apply(self)

        # 初始化布局
        self._initLayout()
        self._connectSignalToSlot()

    def _initLayout(self):

        self._interfaceGroup.addSettingCard(self._themeCard)
        self._interfaceGroup.addSettingCard(self._themeColorCard)
        self._interfaceGroup.addSettingCard(self._zoomCard)

        self._advancedGroup.addSettingCard(self._logCard)

        # 添加设置卡片组到布局
        self.cardGroupsLayout.setSpacing(28)
        self.cardGroupsLayout.setContentsMargins(36, 10, 36, 0)
        self.cardGroupsLayout.addWidget(self._interfaceGroup)
        self.cardGroupsLayout.addWidget(self._advancedGroup)

    def resizeEvent(self, event):
        """动态调整左右边距，让卡片内容区不超过 MAX_CONTENT_WIDTH 并保持水平居中。"""
        super().resizeEvent(event)
        viewport_w = self.viewport().width()
        h_margin = max(36, (viewport_w - self.MAX_CONTENT_WIDTH) // 2)
        self.cardGroupsLayout.setContentsMargins(h_margin, 10, h_margin, 0)

    def _connectSignalToSlot(self):
        # 连接信号
        self._logCard.changePathBtn.clicked.connect(self._on_change_log_path)
        self._logCard.openPathBtn.clicked.connect(self._on_open_log_path)
        self._logCard.clearLogsBtn.clicked.connect(self._on_clear_logs)

        cfg.themeChanged.connect(setTheme)
        self._themeColorCard.colorChanged.connect(lambda c: setThemeColor(c))
        
        # 缩放比例改变提示
        cfg.dpiScale.valueChanged.connect(self._on_dpi_scale_changed)
        # self.micaCard.checkedChanged.connect(signalBus.micaEnableChanged)        

    def _on_dpi_scale_changed(self, scale) -> None:
        InfoBar.success("设置成功", "界面缩放比例已修改，将在重启软件后生效。", parent=self.window())

    def _on_change_log_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择日志保存目录", cfg.logDir.value)
        if path:
            qconfig.set(cfg.logDir, path)
            self._logCard.setLogPath(path)
            logger.info("Log directory changed to %s. It will take effect upon next restart.", path)
            InfoBar.success("设置成功", "新的日志路径已被保存，将在下次启动时生效。", parent=self.window())

    def _on_open_log_path(self) -> None:
        log_dir = cfg.logDir.value
        if os.path.exists(log_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(log_dir))
        else:
            InfoBar.warning("未找到", f"路径不存在：{log_dir}", parent=self.window())

    def _on_clear_logs(self) -> None:
        try:
            count = clear_all_logs()
            if count == 0:
                InfoBar.success("已清理", "当前没有需要清理的日志文件。", parent=self.window())
            else:
                InfoBar.success("清理完毕", f"共清理了 {count} 个历史日志文件（当次运行日志可能因占用无法删除）。", parent=self.window())
        except Exception as e:
            InfoBar.error("清理异常", str(e), parent=self.window())
