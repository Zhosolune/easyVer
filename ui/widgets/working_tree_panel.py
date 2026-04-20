# -*- coding: utf-8 -*-
"""
ui/widgets/working_tree_panel.py
左侧导航面板（包含文件树和表头面包屑）：
  - 顶部显示 BreadcrumbBar 路径导航
  - 点击相互同步选中状态
  - QFileSystemWatcher + 防抖自动刷新
  - 目录颜色继承子文件的变更状态
"""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem

from qfluentwidgets import TreeWidget, BreadcrumbBar, setFont, qconfig, Theme

from core.working_tree import WorkingTreeScanner, FileStatus
from core.workers.scan_worker import ScanWorker
from utils.icon_provider import get_file_icon, get_folder_icon

if TYPE_CHECKING:
    from app.application import EasyVerApp

_COLOR_ADDED    = QColor("#1a7f37")
_COLOR_MODIFIED = QColor("#e36209")
_ROOT_KEY = "__root__"

class WorkingTreePanel(QWidget):
    """文件树 + 面包屑导航表头。"""

    def __init__(self, app: "EasyVerApp", root_path: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._app = app
        self._root_path = root_path
        self._root_name = Path(root_path).resolve().name
        self._worker: Optional[ScanWorker] = None
        self._files_cache: list[FileStatus] = []

        self._setup_ui()

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(500)
        self._debounce.timeout.connect(self.refresh)
        
        qconfig.themeChanged.connect(self._on_theme_changed)
        self._setup_watcher()
        self.refresh()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        # 面包屑表头
        row = QWidget(self)
        row.setFixedHeight(32)
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 8, 0, 8)
        
        self._breadcrumb = BreadcrumbBar(row)
        self._breadcrumb.setSpacing(6)
        self._breadcrumb.blockSignals(True)
        self._breadcrumb.addItem(routeKey=_ROOT_KEY, text=self._root_name)
        self._breadcrumb.blockSignals(False)
        self._breadcrumb.currentItemChanged.connect(self._on_breadcrumb_clicked)
        setFont(self._breadcrumb, 12)
        h.addWidget(self._breadcrumb)
        
        layout.addWidget(row)

        self._tree = TreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree, stretch=1)

    # ------------------------------------------------------------------
    def _setup_watcher(self) -> None:
        self._watcher = QFileSystemWatcher(self)
        root = str(Path(self._root_path).resolve())
        self._watcher.addPath(root)
        try:
            for child in Path(root).iterdir():
                if child.is_dir() and child.name not in {".easyver", ".git", "__pycache__"}:
                    self._watcher.addPath(str(child))
        except PermissionError:
            pass
        self._watcher.directoryChanged.connect(self._on_fs_changed)
        self._watcher.fileChanged.connect(self._on_fs_changed)

    def _on_fs_changed(self, path: str) -> None:
        p = Path(path)
        if p.is_dir() and str(p) not in self._watcher.directories():
            self._watcher.addPath(str(p))
        self._debounce.start()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        conn = self._app.get_conn(self._root_path)
        if conn is None:
            return
        if self._worker and self._worker.isRunning():
            return
        scanner = WorkingTreeScanner(self._root_path, conn)
        self._worker = ScanWorker(scanner)
        self._worker.done.connect(self._populate)
        self._worker.start()

    def cleanup(self) -> None:
        """清理资源（如文件监听器等）。"""
        if hasattr(self, '_watcher'):
            dirs = self._watcher.directories()
            files = self._watcher.files()
            if dirs:
                self._watcher.removePaths(dirs)
            if files:
                self._watcher.removePaths(files)
            self._watcher.deleteLater()
        
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()
            
    # ------------------------------------------------------------------
    def _populate(self, files: list[FileStatus]) -> None:
        self._files_cache = files
        self._tree.clear()
        _dir_nodes: dict[str, QTreeWidgetItem] = {}

        _dir_status: dict[str, str] = {}
        for fs in files:
            if fs.status in ("added", "modified"):
                parts = fs.rel_path.split("/")
                for depth in range(1, len(parts)):
                    key = "/".join(parts[:depth])
                    if _dir_status.get(key) != "added":
                        _dir_status[key] = fs.status

        for fs in files:
            parts = fs.rel_path.split("/")
            parent_item: Optional[QTreeWidgetItem] = None

            for depth, part in enumerate(parts[:-1]):
                key = "/".join(parts[:depth + 1])
                if key not in _dir_nodes:
                    node = QTreeWidgetItem(parent_item or self._tree, [part])
                    node.setIcon(0, get_folder_icon().icon())
                    node.setData(0, Qt.ItemDataRole.UserRole, key)
                    ds = _dir_status.get(key)
                    if ds == "added":
                        node.setForeground(0, _COLOR_ADDED)
                    elif ds == "modified":
                        node.setForeground(0, _COLOR_MODIFIED)
                    _dir_nodes[key] = node
                parent_item = _dir_nodes[key]

            item = QTreeWidgetItem(parent_item or self._tree, [parts[-1]])
            item.setIcon(0, get_file_icon(fs.ext).icon())
            item.setData(0, Qt.ItemDataRole.UserRole, fs.rel_path)
            if fs.status == "added":
                item.setForeground(0, _COLOR_ADDED)
            elif fs.status == "modified":
                item.setForeground(0, _COLOR_MODIFIED)

        self._tree.expandAll()

    def _on_theme_changed(self, theme: Theme) -> None:
        """主题变更时刷新图标。"""
        if self._files_cache:
            self._populate(self._files_cache)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _on_item_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        """收集路径段并更新面包屑。"""
        parts: list[str] = []
        node: Optional[QTreeWidgetItem] = item
        while node is not None:
            parts.insert(0, node.text(0))
            node = node.parent()
            
        self._breadcrumb.blockSignals(True)
        self._breadcrumb.clear()
        self._breadcrumb.addItem(routeKey=_ROOT_KEY, text=self._root_name)
        accumulated = ""
        for part in parts:
            accumulated = f"{accumulated}/{part}" if accumulated else part
            self._breadcrumb.addItem(routeKey=accumulated, text=part)
        self._breadcrumb.blockSignals(False)

    def _on_breadcrumb_clicked(self, route_key: str) -> None:
        """由面包屑点击触发，选中对应树节点。"""
        if route_key == _ROOT_KEY:
            self._tree.clearSelection()
            return

        parts = route_key.split("/")

        def _find(parent, segs: list[str]) -> Optional[QTreeWidgetItem]:
            count = (parent.topLevelItemCount()
                     if hasattr(parent, "topLevelItemCount")
                     else parent.childCount())
            get = (parent.topLevelItem
                   if hasattr(parent, "topLevelItemCount")
                   else parent.child)
            for i in range(count):
                child = get(i)
                if child.text(0) == segs[0]:
                    return child if len(segs) == 1 else _find(child, segs[1:])
            return None

        found = _find(self._tree, parts)
        if found:
            self._tree.setCurrentItem(found)
            self._tree.scrollToItem(found)
