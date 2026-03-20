# -*- coding: utf-8 -*-
"""
ui/dialogs/extract_dialog.py
提取快照文件到指定目录。
"""

import os
from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QWidget, QFileDialog
from qfluentwidgets import MessageBoxBase, SubtitleLabel, LineEdit, PrimaryPushButton, InfoBar

if TYPE_CHECKING:
    from app.application import EasyVerApp


class ExtractDialog(MessageBoxBase):
    def __init__(self, app: "EasyVerApp", root_path: str, snap_id: int, parent: QWidget = None):
        super().__init__(parent)
        self.app = app
        self.root_path = root_path
        self.snap_id = snap_id

        self.titleLabel = SubtitleLabel("提取文件", self)
        self.pathInput = LineEdit(self)
        self.pathInput.setPlaceholderText("选择保存的提取目录...")
        self.btnBrowser = PrimaryPushButton("选择目录", self)
        self.btnBrowser.clicked.connect(self._browse)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.pathInput)
        self.viewLayout.addWidget(self.btnBrowser)

        self.widget.setMinimumWidth(380)
        self.yesButton.setText("提取")
        self.cancelButton.setText("取消")

    def _browse(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择提取位置")
        if dir_path:
            self.pathInput.setText(dir_path)

    def validate(self):
        if not self.pathInput.text().strip():
            return False
        return True

    def accept(self):
        if not self.validate():
            return
            
        target_dir = self.pathInput.text().strip()
        try:
            conn = self.app.get_conn(self.root_path)
            from core.snapshot import SnapshotService
            from db.repositories.file_dao import SnapshotFileDAO
            
            svc = SnapshotService(self.root_path, 1, conn)
            file_dao = SnapshotFileDAO(conn)
            files = file_dao.list_by_snapshot(self.snap_id)
            
            for sf in files:
                if sf.status != "deleted":
                    dest = os.path.join(target_dir, sf.file_path.replace("/", os.sep))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    svc._storage.extract_to(sf.blob_sha256, dest)
            
            InfoBar.success("提取成功", f"文件已保存至: {target_dir}", parent=self.parent())
            super().accept()
        except Exception as e:
            InfoBar.error("提取失败", str(e), parent=self.parent())
            return
