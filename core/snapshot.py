# -*- coding: utf-8 -*-
"""
core/snapshot.py
快照提交与还原服务：
  - commit():   扫描目录 → 增量归档 → 写入 DB
  - restore():  从指定快照还原所有文件到工作目录
  - extract():  提取指定快照中的文件到目标目录（不覆盖工作目录）
"""

import fnmatch
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable

from core.hasher import hash_file
from core.storage import StorageService
from db.connection import DatabaseConnection
from db.repositories.file_dao import BlobDAO, SnapshotFileDAO
from db.repositories.snapshot_dao import SnapshotDAO, SnapshotRecord
from db.repositories.tag_dao import IgnoreRuleDAO

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """扫描目录后，每个文件的元信息。"""
    abs_path: Path
    rel_path: str       # 相对于仓库根目录，使用正斜杠
    name: str
    ext: str            # 小写，含点，如 ".py"
    size: int
    modified_at: int    # mtime，Unix 时间戳（秒）


@dataclass
class CommitResult:
    """commit() 的返回值，包含此次提交的统计信息。"""
    snapshot_id: int
    name: str
    summary: str
    detail: str
    added: int
    modified: int
    deleted: int
    unchanged: int
    total_files: int
    total_size: int
    elapsed_seconds: float


class SnapshotService:
    """
    快照的核心业务逻辑：提交、还原、提取。
    需要传入仓库根目录以及该仓库的 DB 连接。
    """

    def __init__(
        self,
        root_path: str | Path,
        repo_id: int,
        repo_conn: DatabaseConnection,
    ) -> None:
        self._root = Path(root_path).resolve()
        self._repo_id = repo_id
        self._storage = StorageService(
            self._root / ".easyver" / "objects", repo_conn
        )
        self._snapshot_dao = SnapshotDAO(repo_conn)
        self._file_dao = SnapshotFileDAO(repo_conn)
        self._blob_dao = BlobDAO(repo_conn)
        self._ignore_dao = IgnoreRuleDAO(repo_conn)

    # ------------------------------------------------------------------
    # 提交快照
    # ------------------------------------------------------------------
    def commit(
        self,
        name: str,
        summary: str,
        detail: str,
        author: str,
        selected_paths: Optional[list[str]] = None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> CommitResult:
        """
        扫描仓库目录，与上一快照对比后增量归档，生成新快照。

        Args:
            name:           里程碑名称
            summary:        摘要
            detail:         详细说明
            author:         提交者
            selected_paths: v2 选择性提交——只处理这些路径的文件；
                            其余文件从父快照继承（unchanged）。
                            None = 全量提交（旧版默认行为）。
            progress_cb:    可选进度回调 (current_file_index, total_files)
        """
        t0 = time.perf_counter()
        logger.info(
            "Starting commit in repo_id %s (Selective: %s) Name: '%s', Summary: '%s'",
            self._repo_id,
            "Yes" if selected_paths is not None else "No",
            name, summary
        )

        # 1. 读取忽略规则
        patterns = [r.pattern for r in self._ignore_dao.list_active(self._repo_id)]

        # 2. 扫描目录（全量，用于建立文件清单）
        entries = self._scan_directory(patterns)

        # 如果 selected_paths 不为空，只处理被选中的文件
        selected_set: set[str] | None = set(selected_paths) if selected_paths is not None else None

        # 3. 获取父快照的文件清单（用于对比 + 继承未选文件）
        parent_snap = self._snapshot_dao.get_latest(self._repo_id)
        parent_id = parent_snap.id if parent_snap else None
        parent_files: dict[str, str] = {}   # rel_path → sha256
        parent_sizes: dict[str, int] = {}   # rel_path → file_size
        if parent_snap:
            for sf in self._file_dao.list_by_snapshot(parent_snap.id):
                if sf.status != "deleted":
                    parent_files[sf.file_path] = sf.blob_sha256
                    parent_sizes[sf.file_path] = sf.file_size

        # 4. 对比 + 存储（只处理选中的，其余从父快照继承）
        file_records: list[dict] = []
        stats = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}
        total_size = 0
        total_count = len(entries)

        working_paths: set[str] = set()
        for idx, entry in enumerate(entries):
            if progress_cb:
                progress_cb(idx, total_count)
            working_paths.add(entry.rel_path)

            prev_sha256 = parent_files.pop(entry.rel_path, None)

            # 未被选中 → 直接继承父快照版本（unchanged）
            if selected_set is not None and entry.rel_path not in selected_set:
                if prev_sha256 is not None:
                    status = "unchanged"
                    stats["unchanged"] += 1
                    sha256 = prev_sha256
                    self._blob_dao.increment_ref(sha256)
                    total_size += parent_sizes.get(entry.rel_path, 0)
                    file_records.append({
                        "snapshot_id": None, "blob_sha256": sha256,
                        "file_path": entry.rel_path, "file_name": entry.name,
                        "file_ext": entry.ext, "file_size": parent_sizes.get(entry.rel_path, 0),
                        "modified_at": entry.modified_at, "permissions": None, "status": status,
                    })
                # 新文件但未选中 → 不收录进此里程碑
                continue

            sha256 = hash_file(entry.abs_path)

            if prev_sha256 is None:
                status = "added"
                stats["added"] += 1
                self._storage.store_file(entry.abs_path)
            elif prev_sha256 != sha256:
                status = "modified"
                stats["modified"] += 1
                self._storage.store_file(entry.abs_path)
            else:
                status = "unchanged"
                stats["unchanged"] += 1
                self._blob_dao.increment_ref(sha256)

            total_size += entry.size
            file_records.append({
                "snapshot_id": None, "blob_sha256": sha256,
                "file_path": entry.rel_path, "file_name": entry.name,
                "file_ext": entry.ext, "file_size": entry.size,
                "modified_at": entry.modified_at, "permissions": None, "status": status,
            })

        # 5. 处理全量模式下的已删除文件（selected_paths 模式不处理删除）
        if selected_set is None:
            for del_path, del_sha256 in parent_files.items():
                stats["deleted"] += 1
                file_records.append({
                    "snapshot_id": None, "blob_sha256": del_sha256,
                    "file_path": del_path, "file_name": Path(del_path).name,
                    "file_ext": Path(del_path).suffix.lower(),
                    "file_size": 0, "modified_at": 0, "permissions": None, "status": "deleted",
                })

        # 6. 插入快照主记录
        snapshot_id = self._snapshot_dao.insert(
            repo_id=self._repo_id, name=name, summary=summary, detail=detail, author=author,
            total_files=len(file_records), total_size=total_size, parent_id=parent_id,
        )

        # 7. 批量插入文件清单
        for rec in file_records:
            rec["snapshot_id"] = snapshot_id
        self._file_dao.insert_many(file_records)

        elapsed = time.perf_counter() - t0
        
        # 记录详细的操作日志
        logger.info(
            "Snapshot created: ID=%d, Name='%s', Summary='%s', Added=%d, Modified=%d, Deleted=%d, Unchanged=%d, Time=%.3fs",
            snapshot_id, name, summary, stats["added"], stats["modified"], stats["deleted"], stats["unchanged"], elapsed
        )
        
        return CommitResult(
            snapshot_id=snapshot_id, name=name, summary=summary, detail=detail, added=stats["added"], modified=stats["modified"],
            deleted=stats["deleted"], unchanged=stats["unchanged"],
            total_files=len(file_records), total_size=total_size, elapsed_seconds=elapsed,
        )

    # ------------------------------------------------------------------
    # 还原快照（覆盖工作目录）
    # ------------------------------------------------------------------
    def restore(
        self,
        snapshot_id: int,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """将工作目录还原为指定快照的状态（不删除快照里不存在的文件）。"""
        logger.info("Starting full restore for snapshot #%d", snapshot_id)
        files = self._file_dao.list_by_snapshot(snapshot_id)
        active = [f for f in files if f.status != "deleted"]
        for idx, sf in enumerate(active):
            if progress_cb:
                progress_cb(idx, len(active))
            dest = self._root / sf.file_path.replace("/", os.sep)
            self._storage.extract_to(sf.blob_sha256, dest)
        logger.info("Restored snapshot #%d (%d files)", snapshot_id, len(active))

    # ------------------------------------------------------------------
    # 提取指定文件（不覆盖工作目录）
    # ------------------------------------------------------------------
    def extract_file(
        self,
        snapshot_id: int,
        rel_file_path: str,
        dest_dir: str | Path,
    ) -> Path:
        """
        从快照中提取单个文件到 dest_dir，文件名保持原名。
        Returns:
            实际写入的完整路径。
        """
        logger.info("Extracting file '%s' from snapshot #%d to %s", rel_file_path, snapshot_id, dest_dir)
        sf = self._file_dao.get_by_path(snapshot_id, rel_file_path)
        if sf is None:
            raise FileNotFoundError(f"快照 #{snapshot_id} 中未找到文件：{rel_file_path}")
        dest = Path(dest_dir) / sf.file_name
        self._storage.extract_to(sf.blob_sha256, dest)
        return dest

    # ------------------------------------------------------------------
    # 扫描目录
    # ------------------------------------------------------------------
    def _scan_directory(self, ignore_patterns: list[str]) -> list[FileEntry]:
        """
        递归扫描仓库根目录，跳过 .easyver/ 和匹配忽略规则的路径。
        Returns:
            按相对路径排序的 FileEntry 列表。
        """
        entries: list[FileEntry] = []
        for abs_path in self._root.rglob("*"):
            if not abs_path.is_file():
                continue

            # 始终跳过 .easyver 目录
            try:
                rel = abs_path.relative_to(self._root)
            except ValueError:
                continue
            if rel.parts[0] == ".easyver":
                continue

            rel_str = "/".join(rel.parts)

            # 应用忽略规则
            if any(fnmatch.fnmatch(rel_str, p) for p in ignore_patterns):
                continue

            stat = abs_path.stat()
            entries.append(FileEntry(
                abs_path=abs_path,
                rel_path=rel_str,
                name=abs_path.name,
                ext=abs_path.suffix.lower(),
                size=stat.st_size,
                modified_at=int(stat.st_mtime),
            ))

        entries.sort(key=lambda e: e.rel_path)
        return entries
