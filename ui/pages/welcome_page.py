# -*- coding: utf-8 -*-
"""
v2/ui/pages/welcome_page.py
欢迎/启动页：新建仓库、打开仓库、最近仓库列表。
"""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog

from qfluentwidgets import (
    ScrollArea, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, CaptionLabel, FluentIcon, InfoBar,
)

from app.app_config import cfg

from app.style_sheet import StyleSheet



import logging
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.application import EasyVerApp


class WelcomePage(ScrollArea):
    """欢迎页：新建 / 打开 / 最近仓库。"""

    repo_opened = pyqtSignal(str)   # 发出 root_path → 主窗口新增导航项

    def __init__(self, app_instance: EasyVerApp, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._app = app_instance
        self.setObjectName("welcomePage")
        StyleSheet.WELCOME_PAGE.apply(self)
        self._setup_ui()

    def _setup_ui(self) -> None:
        container = QWidget(self)
        outer = QVBoxLayout(container)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QWidget(container)
        card.setObjectName("welcomeCard")
        card.setFixedWidth(460)
        from PyQt6.QtWidgets import QVBoxLayout as VBox
        cl = VBox(card)
        cl.setSpacing(12)
        cl.setContentsMargins(48, 48, 48, 48)

        # ── Logo ────────────────────────────────────────
        logo = QLabel("🗂", card)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(); f.setPointSize(52); logo.setFont(f)

        title = TitleLabel("EasyVer", card)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = CaptionLabel("本地文件版本管理工具", card)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cl.addWidget(logo)
        cl.addWidget(title)
        cl.addWidget(sub)
        cl.addSpacing(16)

        # ── 主操作按钮 ───────────────────────────────────
        btn_new = PrimaryPushButton(FluentIcon.ADD, "  新建仓库", card)
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setFixedHeight(42)
        btn_new.clicked.connect(self._on_new_repo)

        btn_open = PushButton(FluentIcon.FOLDER_ADD, "  打开已有仓库目录", card)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(42)
        btn_open.clicked.connect(self._on_open_repo)

        cl.addWidget(btn_new)
        cl.addWidget(btn_open)

        # ── 最近仓库 ─────────────────────────────────────
        recents = cfg.recentRepos.value
        if recents:
            cl.addSpacing(12)
            cl.addWidget(CaptionLabel("最近打开：", card))
            for path in recents[:6]:
                p = Path(path)
                btn = PushButton(FluentIcon.HISTORY, f"  {p.name}", card)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(str(p))
                btn.setFixedHeight(36)
                btn.clicked.connect(lambda _, rp=path: self._open(rp))
                cl.addWidget(btn)

        outer.addStretch(1)
        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        self.setWidget(container)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

    # ------------------------------------------------------------------
    def _on_new_repo(self) -> None:
        from ui.dialogs.new_repo_dialog import NewRepoDialog
        dlg = NewRepoDialog(self.window())
        if dlg.exec() and dlg.validate():
            logger.info("Initializing new repo: '%s' at %s", dlg.repo_name, dlg.repo_path)
            try:
                self._app.create_repo(dlg.repo_path, dlg.repo_name, dlg.repo_desc)
                self.repo_opened.emit(dlg.repo_path)
            except Exception as e:
                logger.error("Failed to create new repo: %s", e, exc_info=True)
                InfoBar.error("创建失败", str(e), parent=self.window())

    def _on_open_repo(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择仓库根目录")
        if path:
            logger.info("User picked repository directory: %s", path)
            self._open(path)

    def _open(self, path: str) -> None:
        try:
            logger.info("Opening repository from WelcomePage: %s", path)
            self._app.open_repo(path)
            self.repo_opened.emit(path)
        except Exception as e:
            logger.error("Failed to open repository %s: %s", path, e, exc_info=True)
            InfoBar.error("打开失败", str(e), parent=self.window())
