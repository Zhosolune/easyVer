# -*- coding: utf-8 -*-
"""v2/ui/dialogs/new_repo_dialog.py — 新建仓库对话框（复用父目录原有实现样式）。"""

import os
from typing import Optional

from PyQt6.QtWidgets import QWidget, QFileDialog
from qfluentwidgets import (
    MessageBox, LineEdit, TextEdit, PushButton, BodyLabel, FluentIcon,
)


class NewRepoDialog(MessageBox):
    """新建仓库对话框。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("新建仓库", "", parent)
        self._setup_body()
        self.yesButton.setText("创建")
        self.cancelButton.setText("取消")

    def _setup_body(self) -> None:
        self._name_edit = LineEdit(self)
        self._name_edit.setPlaceholderText("仓库名称")

        self._path_edit = LineEdit(self)
        self._path_edit.setPlaceholderText("仓库根目录路径")
        self._path_edit.setReadOnly(True)

        self._browse_btn = PushButton(FluentIcon.FOLDER, "浏览", self)
        self._browse_btn.clicked.connect(self._pick_directory)

        self._desc_edit = TextEdit(self)
        self._desc_edit.setPlaceholderText("描述（可选）")
        self._desc_edit.setFixedHeight(70)

        self.textLayout.addWidget(BodyLabel("名称：", self))
        self.textLayout.addWidget(self._name_edit)
        self.textLayout.addWidget(BodyLabel("目录：", self))
        self.textLayout.addWidget(self._path_edit)
        self.textLayout.addWidget(self._browse_btn)
        self.textLayout.addWidget(BodyLabel("描述：", self))
        self.textLayout.addWidget(self._desc_edit)

    def _pick_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            self._path_edit.setText(path)
            if not self._name_edit.text().strip():
                self._name_edit.setText(os.path.basename(path))

    @property
    def repo_name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def repo_path(self) -> str:
        return self._path_edit.text().strip()

    @property
    def repo_desc(self) -> str:
        return self._desc_edit.toPlainText().strip()

    def validate(self) -> bool:
        return bool(self.repo_name and self.repo_path)
