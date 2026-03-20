# -*- coding: utf-8 -*-
"""
db/repositories/file_dao.py
blobs 表 + snapshot_files 表的数据访问对象（DAO）。
"""

import time
from dataclasses import dataclass
from typing import Optional

from db.connection import DatabaseConnection


# ─────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────

@dataclass
class BlobRecord:
    """对应 blobs 表的一行数据。"""
    sha256: str
    size_original: int
    size_compressed: int
    object_path: str
    ref_count: int
    created_at: int


@dataclass
class SnapshotFileRecord:
    """对应 snapshot_files 表的一行数据。"""
    id: int
    snapshot_id: int
    blob_sha256: str
    file_path: str
    file_name: str
    file_ext: str
    file_size: int
    modified_at: int
    permissions: Optional[str]
    status: str   # added / modified / deleted / unchanged


# ─────────────────────────────────────────
# BlobDAO
# ─────────────────────────────────────────

class BlobDAO:
    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def exists(self, sha256: str) -> bool:
        """判断某 blob 是否已存在（内容去重查询）。"""
        row = self._conn.fetchone(
            "SELECT 1 FROM blobs WHERE sha256=?", (sha256,)
        )
        return row is not None

    def insert(
        self,
        sha256: str,
        size_original: int,
        size_compressed: int,
        object_path: str,
    ) -> None:
        """写入 blob 记录（sha256 已存在时忽略）。"""
        now = int(time.time())
        self._conn.execute(
            """
            INSERT OR IGNORE INTO blobs
                (sha256, size_original, size_compressed, object_path, ref_count, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (sha256, size_original, size_compressed, object_path, now),
            commit=True,
        )

    def get(self, sha256: str) -> Optional[BlobRecord]:
        """按 SHA-256 获取 blob 记录。"""
        row = self._conn.fetchone("SELECT * FROM blobs WHERE sha256=?", (sha256,))
        return self._row_to_blob(row) if row else None

    def increment_ref(self, sha256: str) -> None:
        """引用计数 +1。"""
        self._conn.execute(
            "UPDATE blobs SET ref_count = ref_count + 1 WHERE sha256=?",
            (sha256,),
            commit=True,
        )

    def decrement_ref(self, sha256: str) -> None:
        """引用计数 -1（不低于 0）。"""
        self._conn.execute(
            "UPDATE blobs SET ref_count = MAX(0, ref_count - 1) WHERE sha256=?",
            (sha256,),
            commit=True,
        )

    def list_orphans(self) -> list[BlobRecord]:
        """列出所有引用计数为 0 的孤立 blob（GC 候选）。"""
        rows = self._conn.fetchall("SELECT * FROM blobs WHERE ref_count = 0")
        return [self._row_to_blob(r) for r in rows]

    def delete(self, sha256: str) -> None:
        """删除 blob 元数据记录（物理文件由 StorageService 处理）。"""
        self._conn.execute(
            "DELETE FROM blobs WHERE sha256=?", (sha256,), commit=True
        )

    def total_size_original(self) -> int:
        """所有 blob 原始总大小（字节）。"""
        row = self._conn.fetchone("SELECT COALESCE(SUM(size_original),0) AS s FROM blobs")
        return row["s"] if row else 0

    def total_size_compressed(self) -> int:
        """所有 blob 压缩后总大小（字节）。"""
        row = self._conn.fetchone("SELECT COALESCE(SUM(size_compressed),0) AS s FROM blobs")
        return row["s"] if row else 0

    @staticmethod
    def _row_to_blob(row) -> BlobRecord:
        return BlobRecord(
            sha256=row["sha256"],
            size_original=row["size_original"],
            size_compressed=row["size_compressed"],
            object_path=row["object_path"],
            ref_count=row["ref_count"],
            created_at=row["created_at"],
        )


# ─────────────────────────────────────────
# SnapshotFileDAO
# ─────────────────────────────────────────

class SnapshotFileDAO:
    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def insert_many(self, records: list[dict]) -> None:
        """
        批量插入快照文件记录。
        records 中每个 dict 包含 snapshot_files 对应字段。
        """
        self._conn.executemany(
            """
            INSERT INTO snapshot_files
                (snapshot_id, blob_sha256, file_path, file_name, file_ext,
                 file_size, modified_at, permissions, status)
            VALUES
                (:snapshot_id, :blob_sha256, :file_path, :file_name, :file_ext,
                 :file_size, :modified_at, :permissions, :status)
            """,
            records,
            commit=True,
        )

    def list_by_snapshot(self, snapshot_id: int) -> list[SnapshotFileRecord]:
        """列出某快照的所有文件记录。"""
        rows = self._conn.fetchall(
            "SELECT * FROM snapshot_files WHERE snapshot_id=? ORDER BY file_path",
            (snapshot_id,),
        )
        return [self._row_to_record(r) for r in rows]

    def list_changed(self, snapshot_id: int) -> list[SnapshotFileRecord]:
        """只列出状态为 added/modified/deleted 的文件（即实际变更的文件）。"""
        rows = self._conn.fetchall(
            """
            SELECT * FROM snapshot_files
            WHERE snapshot_id=? AND status != 'unchanged'
            ORDER BY file_path
            """,
            (snapshot_id,),
        )
        return [self._row_to_record(r) for r in rows]

    def get_by_path(
        self, snapshot_id: int, file_path: str
    ) -> Optional[SnapshotFileRecord]:
        """在指定快照中按路径精确查找一条记录。"""
        row = self._conn.fetchone(
            "SELECT * FROM snapshot_files WHERE snapshot_id=? AND file_path=?",
            (snapshot_id, file_path),
        )
        return self._row_to_record(row) if row else None

    def list_blob_sha256s(self, snapshot_id: int) -> list[str]:
        """列出某快照引用的所有 blob sha256（用于引用计数更新）。"""
        rows = self._conn.fetchall(
            "SELECT DISTINCT blob_sha256 FROM snapshot_files WHERE snapshot_id=?",
            (snapshot_id,),
        )
        return [r["blob_sha256"] for r in rows]

    def count_by_repo_snapshot(self, repo_id: int) -> dict[int, int]:
        """一次性查询某仓库下每个快照的文件总数。
        
        Returns:
            dict: {snapshot_id: file_count}
        """
        rows = self._conn.fetchall(
            """
            SELECT sf.snapshot_id, COUNT(*) AS cnt
            FROM snapshot_files sf
            INNER JOIN snapshots s ON sf.snapshot_id = s.id
            WHERE s.repo_id = ?
            GROUP BY sf.snapshot_id
            """,
            (repo_id,),
        )
        return {r["snapshot_id"]: r["cnt"] for r in rows}

    @staticmethod
    def _row_to_record(row) -> SnapshotFileRecord:
        return SnapshotFileRecord(
            id=row["id"],
            snapshot_id=row["snapshot_id"],
            blob_sha256=row["blob_sha256"],
            file_path=row["file_path"],
            file_name=row["file_name"],
            file_ext=row["file_ext"],
            file_size=row["file_size"],
            modified_at=row["modified_at"],
            permissions=row["permissions"],
            status=row["status"],
        )
