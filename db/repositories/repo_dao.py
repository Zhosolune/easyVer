# -*- coding: utf-8 -*-
"""
db/repositories/repo_dao.py
repositories 表的数据访问对象（DAO）。
"""

import time
from dataclasses import dataclass
from typing import Optional

from db.connection import DatabaseConnection


@dataclass
class RepoRecord:
    """对应 repositories 表的一行数据。"""
    id: int
    name: str
    root_path: str
    description: str
    created_at: int
    updated_at: int


class RepoDAO:
    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def insert(self, name: str, root_path: str, description: str = "") -> int:
        """新建仓库记录，返回新行 id。"""
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO repositories(name, root_path, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, root_path, description, now, now),
            commit=True,
        )
        return self._conn.last_insert_rowid()

    def get_by_id(self, repo_id: int) -> Optional[RepoRecord]:
        """按 ID 查询仓库。"""
        row = self._conn.fetchone(
            "SELECT * FROM repositories WHERE id = ?", (repo_id,)
        )
        return self._row_to_record(row) if row else None

    def get_by_path(self, root_path: str) -> Optional[RepoRecord]:
        """按根目录路径查询仓库。"""
        row = self._conn.fetchone(
            "SELECT * FROM repositories WHERE root_path = ?", (root_path,)
        )
        return self._row_to_record(row) if row else None

    def list_all(self) -> list[RepoRecord]:
        """列出所有仓库（按创建时间升序）。"""
        rows = self._conn.fetchall(
            "SELECT * FROM repositories ORDER BY created_at ASC"
        )
        return [self._row_to_record(r) for r in rows]

    def update_name_description(
        self, repo_id: int, name: str, description: str
    ) -> None:
        """更新仓库名称和描述。"""
        now = int(time.time())
        self._conn.execute(
            "UPDATE repositories SET name=?, description=?, updated_at=? WHERE id=?",
            (name, description, now, repo_id),
            commit=True,
        )

    def touch_updated_at(self, repo_id: int) -> None:
        """更新仓库的最后操作时间。"""
        self._conn.execute(
            "UPDATE repositories SET updated_at=? WHERE id=?",
            (int(time.time()), repo_id),
            commit=True,
        )

    def delete(self, repo_id: int) -> None:
        """删除仓库（级联删除所有快照等子记录）。"""
        self._conn.execute(
            "DELETE FROM repositories WHERE id=?", (repo_id,), commit=True
        )

    @staticmethod
    def _row_to_record(row) -> RepoRecord:
        return RepoRecord(
            id=row["id"],
            name=row["name"],
            root_path=row["root_path"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
