# -*- coding: utf-8 -*-
"""
db/repositories/snapshot_dao.py
snapshots 表的数据访问对象（DAO）。
"""

import time
from dataclasses import dataclass
from typing import Optional

from db.connection import DatabaseConnection


@dataclass
class SnapshotRecord:
    """对应 snapshots 表的一行数据。"""
    id: int
    repo_id: int
    parent_id: Optional[int]
    name: str
    summary: str
    detail: str
    author: str
    total_files: int
    total_size: int
    created_at: int
    hash_id: str


class SnapshotDAO:
    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def insert(
        self,
        repo_id: int,
        name: str,
        summary: str,
        detail: str,
        author: str,
        total_files: int,
        total_size: int,
        parent_id: Optional[int] = None,
    ) -> int:
        """插入快照记录，返回新行 id。"""
        now = int(time.time())
        import secrets
        hash_id = secrets.token_hex(4)

        self._conn.execute(
            """
            INSERT INTO snapshots
                (repo_id, parent_id, name, summary, detail, author, total_files, total_size, created_at, hash_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (repo_id, parent_id, name, summary, detail, author, total_files, total_size, now, hash_id),
            commit=True,
        )
        return self._conn.last_insert_rowid()

    def get_by_id(self, snapshot_id: int) -> Optional[SnapshotRecord]:
        """按 ID 查询快照。"""
        row = self._conn.fetchone(
            "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
        )
        return self._row_to_record(row) if row else None

    def list_by_repo(self, repo_id: int) -> list[SnapshotRecord]:
        """列出某仓库的所有快照（按时间降序，最新在前）。"""
        rows = self._conn.fetchall(
            "SELECT * FROM snapshots WHERE repo_id=? ORDER BY created_at DESC",
            (repo_id,),
        )
        return [self._row_to_record(r) for r in rows]

    def get_latest(self, repo_id: int) -> Optional[SnapshotRecord]:
        """获取某仓库的最新快照。"""
        row = self._conn.fetchone(
            "SELECT * FROM snapshots WHERE repo_id=? ORDER BY created_at DESC LIMIT 1",
            (repo_id,),
        )
        return self._row_to_record(row) if row else None

    def count_by_repo(self, repo_id: int) -> int:
        """统计某仓库的快照数量。"""
        row = self._conn.fetchone(
            "SELECT COUNT(*) AS cnt FROM snapshots WHERE repo_id=?", (repo_id,)
        )
        return row["cnt"] if row else 0

    def delete(self, snapshot_id: int) -> None:
        """删除快照（级联删除 snapshot_files 记录）。"""
        self._conn.execute(
            "DELETE FROM snapshots WHERE id=?", (snapshot_id,), commit=True
        )

    def update_metadata(self, snapshot_id: int, name: str, summary: str, detail: str) -> None:
        """修改快照的名称、摘要与详细说明。"""
        self._conn.execute(
            "UPDATE snapshots SET name=?, summary=?, detail=? WHERE id=?",
            (name, summary, detail, snapshot_id),
            commit=True,
        )

    @staticmethod
    def _row_to_record(row) -> SnapshotRecord:
        return SnapshotRecord(
            id=row["id"],
            repo_id=row["repo_id"],
            parent_id=row["parent_id"],
            name=row["name"],
            summary=row["summary"],
            detail=row["detail"],
            author=row["author"],
            total_files=row["total_files"],
            total_size=row["total_size"],
            created_at=row["created_at"],
            hash_id=row["hash_id"] if "hash_id" in row.keys() else "",
        )
