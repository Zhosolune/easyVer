# -*- coding: utf-8 -*-
"""
v2/core/working_tree.py
实时工作目录扫描：将工作目录文件与最新里程碑对比，返回每个文件的状态。
状态：
  added     — 工作目录有，最新里程碑无（绿色显示）
  modified  — 工作目录与最新里程碑内容哈希不同（橙色显示）
  unchanged — 内容相同（正常显示）
不显示 deleted（里程碑有、工作目录无）。
"""

from dataclasses import dataclass
from pathlib import Path

from core.hasher import hash_file                    # 复用父目录 core
from db.connection import DatabaseConnection          # 复用父目录 db


@dataclass
class FileStatus:
    rel_path: str          # 相对路径（使用 / 分隔符）
    status: str            # "added" | "modified" | "unchanged"
    size: int              # 字节数
    abs_path: Path         # 绝对路径（供UI直接使用）

    @property
    def ext(self) -> str:
        return Path(self.rel_path).suffix.lower()

    @property
    def name(self) -> str:
        return Path(self.rel_path).name


class WorkingTreeScanner:
    """扫描仓库工作目录，与最新里程碑对比，返回文件状态列表。"""

    # 固定忽略的目录/文件名
    _IGNORE_DIRS = {".easyver", ".git", "__pycache__", ".venv", "node_modules"}

    def __init__(self, root_path: str | Path, conn: DatabaseConnection) -> None:
        self._root = Path(root_path).resolve()
        self._conn = conn

    def scan(self) -> list[FileStatus]:
        """
        扫描工作目录，返回 FileStatus 列表（不含 deleted 状态）。
        首次扫描（无里程碑）时所有文件状态都是 added。
        """
        # ── 最新里程碑的文件清单 ──────────────────────────
        prev_hashes: dict[str, str] = {}   # rel_path → sha256
        prev_sizes: dict[str, int] = {}    # rel_path → size
        prev_mtimes: dict[str, int] = {}   # rel_path → modified_at
        latest_snap = self._get_latest_snapshot()
        if latest_snap is not None:
            from db.repositories.file_dao import SnapshotFileDAO
            dao = SnapshotFileDAO(self._conn)
            for sf in dao.list_by_snapshot(latest_snap):
                prev_hashes[sf.file_path] = sf.blob_sha256
                prev_sizes[sf.file_path] = sf.file_size
                prev_mtimes[sf.file_path] = sf.modified_at

        # ── 扫描工作目录 ──────────────────────────────────
        result: list[FileStatus] = []
        for abs_path in self._iter_files():
            if not abs_path.is_file():
                continue
            rel = str(abs_path.relative_to(self._root)).replace("\\", "/")
            stat = abs_path.stat()
            size = stat.st_size
            mtime = int(stat.st_mtime)

            if rel not in prev_hashes:
                status = "added"
            else:
                # 惰性比较：先比大小和修改时间
                if size != prev_sizes.get(rel, -1):
                    status = "modified"
                elif mtime == prev_mtimes.get(rel, -1):
                    # 大小和时间都没变，认为未修改
                    status = "unchanged"
                else:
                    cur_hash = hash_file(abs_path)
                    status = "unchanged" if cur_hash == prev_hashes[rel] else "modified"

            result.append(FileStatus(rel, status, size, abs_path))

        result.sort(key=lambda f: (f.rel_path.count("/"), f.rel_path))
        return result

    def get_changed(self) -> list[FileStatus]:
        """只返回 added / modified 的文件（供创建里程碑对话框使用）。"""
        return [f for f in self.scan() if f.status != "unchanged"]

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _get_latest_snapshot(self):
        """返回最新快照 ID，或 None。"""
        from db.repositories.snapshot_dao import SnapshotDAO
        dao = SnapshotDAO(self._conn)
        snaps = dao.list_by_repo(1)  # repo-level DB 固定 repo_id=1
        return snaps[0].id if snaps else None

        return snaps[0].id if snaps else None

    def _iter_files(self):
        """递归遍历工作目录，跳过忽略目录。"""
        for item in self._root.rglob("*"):
            # 忽略规则：若路径中任何部分在忽略集中则跳过
            if any(part in self._IGNORE_DIRS for part in item.parts):
                continue
            if item.is_file():
                yield item
