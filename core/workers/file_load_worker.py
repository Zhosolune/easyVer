# -*- coding: utf-8 -*-
"""
core/workers/file_load_worker.py
后台线程，用于异步加载里程碑文件变更并构建树状节点结构。
"""

from PyQt6.QtCore import QThread, pyqtSignal

class TreeNode:
    """用于构建文件变更树状视图的节点模型"""
    def __init__(self, name: str):
        self.name = name
        self.children: dict[str, 'TreeNode'] = {}
        self.files: list = []    # list of SnapshotFileRecord
        self.all_files_count = 0
        self.added_count = 0
        self.deleted_count = 0
        self.modified_count = 0

class FileLoadWorker(QThread):
    """异步查询数据库并构建文件变更列表与树状节点的 Worker 线程"""
    # 信号传递参数：changed_files(list), root_node(TreeNode), added(int), modified(int), deleted(int)
    finished = pyqtSignal(list, TreeNode, int, int, int)

    def __init__(self, root_path: str, snap_id: int, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.snap_id = snap_id

    def run(self):
        from db.connection import DatabaseConnection
        from db.repositories.file_dao import SnapshotFileDAO
        
        # 修正数据库文件名为 easyver.db
        conn = DatabaseConnection(f"{self.root_path}/.easyver/easyver.db")
        files = SnapshotFileDAO(conn).list_by_snapshot(self.snap_id)
        conn.close()

        added = 0
        deleted = 0
        modified = 0
        
        changed_files = []
        for f in files:
            if f.status == 'unchanged':
                continue
            changed_files.append(f)
            if f.status == 'added': added += 1
            elif f.status == 'deleted': deleted += 1
            elif f.status == 'modified': modified += 1

        root_node = TreeNode("")
        for f in changed_files:
            parts = f.file_path.split('/')
            curr = root_node
            for part in parts[:-1]:
                if part not in curr.children:
                    curr.children[part] = TreeNode(part)
                curr = curr.children[part]
                curr.all_files_count += 1
                if f.status == 'added': curr.added_count += 1
                elif f.status == 'deleted': curr.deleted_count += 1
                elif f.status == 'modified': curr.modified_count += 1
            curr.files.append(f)
            curr.all_files_count += 1
            if f.status == 'added': curr.added_count += 1
            elif f.status == 'deleted': curr.deleted_count += 1
            elif f.status == 'modified': curr.modified_count += 1

        self.finished.emit(changed_files, root_node, added, modified, deleted)