# -*- coding: utf-8 -*-
"""
v2/ui/main_window.py
动态导航主窗口：
  - 欢迎页（固定首项）
  - 每个仓库对应一个侧边栏导航项（运行时动态添加/移除）
  - 设置页（固定末项）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon,
    InfoBar, InfoBarPosition, SystemThemeListener, SplashScreen
)

from ui.pages.welcome_page import WelcomePage
from ui.pages.repo_page import RepoPage
from ui.pages.settings_page import SettingPage

if TYPE_CHECKING:
    from app.application import EasyVerApp


class MainWindow(MSFluentWindow):
    """EasyVer v2 主窗口，动态侧边栏。"""

    def __init__(self, app_instance: EasyVerApp) -> None:
        super().__init__()
        self._setup_window()

        self._app = app_instance
        self._repo_pages: dict[str, RepoPage] = {}   # root_path → RepoPage
        self.themeListener = SystemThemeListener(self)

        self._setup_static_pages()
        self._restore_session()
        self.connectSignalToSlot()

        timer = QTimer()
        timer.singleShot(1000, self.splashScreen.finish)
        # self.splashScreen.finish()

        self.themeListener.start()

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def _setup_window(self) -> None:
        self.setWindowIcon(QIcon(':/easyVer/images/logo.png'))
        self.setWindowTitle("EasyVer")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        
        # 启动页
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(120, 120))
        self.splashScreen.raise_()
        
        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

    def _setup_static_pages(self) -> None:
        # 欢迎页
        self._welcome_page = WelcomePage(self._app, self)
        self.addSubInterface(
            self._welcome_page, FluentIcon.HOME, "主页",
            position=NavigationItemPosition.TOP,
        )

        # 设置页
        self._settings_page = SettingPage(self)
        self.addSubInterface(
            self._settings_page, FluentIcon.SETTING, "设置",
            position=NavigationItemPosition.BOTTOM,
        )

    def connectSignalToSlot(self) -> None:
        """连接信号到槽函数。"""
        self._welcome_page.repo_opened.connect(self.add_repo_page)

    def _restore_session(self) -> None:
        """恢复上次会话中打开的所有仓库。"""
        opened = self._app.restore_last_session()
        for path in opened:
            record = self._app.get_record(path)
            if record:
                self._add_repo_nav(path, record.name)

    # ------------------------------------------------------------------
    # 仓库导航项管理
    # ------------------------------------------------------------------
    def add_repo_page(self, root_path: str) -> None:
        """添加仓库导航项（由欢迎页信号触发）。"""
        if root_path in self._repo_pages:
            # 已存在则直接切换
            self.switchTo(self._repo_pages[root_path])
            return
        record = self._app.get_record(root_path)
        if record is None:
            return
        self._add_repo_nav(root_path, record.name)
        # 切换到新添加的仓库页
        self.switchTo(self._repo_pages[root_path])

    def _add_repo_nav(self, root_path: str, name: str) -> None:
        """创建 RepoPage 并注册到导航栏。"""
        page = RepoPage(self._app, root_path, self)
        route_key = f"repo_{root_path.replace(':', '').replace('/', '_').replace(chr(92), '_')}"
        page.setObjectName(route_key)
        self._repo_pages[root_path] = page
        self.addSubInterface(
            page, FluentIcon.FOLDER, name,
            position=NavigationItemPosition.TOP,
        )
        
        # 获取导航项并绑定右键菜单
        item_widget = self.navigationInterface.widget(route_key)
        if item_widget:
            item_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            item_widget.customContextMenuRequested.connect(
                lambda pos, rp=root_path, w=item_widget: self._show_repo_context_menu(rp, w.mapToGlobal(pos))
            )

    def _show_repo_context_menu(self, root_path: str, pos) -> None:
        from qfluentwidgets import RoundMenu, Action, MessageBox, FluentIcon
        
        menu = RoundMenu(parent=self)
        
        # 删除仓库菜单项
        delete_action = Action(FluentIcon.DELETE, "删除仓库", self)
        
        def on_delete():
            title = "删除仓库"
            content = "确定要从应用中移除该仓库吗？\n\n注意：这将会彻底删除该仓库的所有版本记录和 .easyver 配置文件，但不会删除您工作目录中的实际文件。"
            w = MessageBox(title, content, self)
            if w.exec():
                # 先切换到欢迎页
                self.switchTo(self._welcome_page)
                # 从 UI 移除
                if root_path in self._repo_pages:
                    page = self._repo_pages.pop(root_path)
                    self.removeInterface(page)
                    page.cleanup()
                    page.deleteLater()
                # 从应用彻底删除
                self._app.delete_repo(root_path)
                
                # 刷新欢迎页最近记录
                self._welcome_page.refresh_recent()
                self.show_success("已删除仓库", f"仓库 {root_path} 已移除")
                
        delete_action.triggered.connect(on_delete)
        menu.addAction(delete_action)
        menu.exec(pos)

    def remove_repo_page(self, root_path: str) -> None:
        """从导航栏移除仓库（关闭仓库时调用）。"""
        self.switchTo(self._welcome_page)
        if root_path in self._repo_pages:
            page = self._repo_pages.pop(root_path)
            self.removeInterface(page)
            page.cleanup()
            page.deleteLater()
        self._app.close_repo(root_path)

    # ------------------------------------------------------------------
    # 通知工具
    # ------------------------------------------------------------------
    def show_success(self, title: str, content: str = "") -> None:
        InfoBar.success(title, content, duration=3000,
                        position=InfoBarPosition.TOP_RIGHT, parent=self)

    def show_error(self, title: str, content: str = "") -> None:
        InfoBar.error(title, content, duration=5000,
                      position=InfoBarPosition.TOP_RIGHT, parent=self)

    def show_info(self, title: str, content: str = "") -> None:
        InfoBar.info(title, content, duration=2500,
                     position=InfoBarPosition.TOP_RIGHT, parent=self)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        self._app.shutdown()
        super().closeEvent(event)
