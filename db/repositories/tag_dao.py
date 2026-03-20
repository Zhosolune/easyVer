# -*- coding: utf-8 -*-
"""
db/repositories/tag_dao.py
tags 表 + ignore_rules 表的数据访问对象（DAO）。
"""

import time
from dataclasses import dataclass
from typing import Optional

from db.connection import DatabaseConnection


@dataclass
class TagRecord:
    """对应 tags 表的一行数据。"""
    id: int
    repo_id: int
    snapshot_id: int
    name: str
    color: str
    description: str
    created_at: int


@dataclass
class IgnoreRuleRecord:
    """对应 ignore_rules 表的一行数据。"""
    id: int
    repo_id: int
    pattern: str
    is_active: bool
    created_at: int


class TagDAO:
    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def insert(
        self,
        repo_id: int,
        snapshot_id: int,
        name: str,
        color: str = "#5B9BD5",
        description: str = "",
    ) -> int:
        """新建标签，返回新行 id。"""
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO tags(repo_id, snapshot_id, name, color, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (repo_id, snapshot_id, name, color, description, now),
            commit=True,
        )
        return self._conn.last_insert_rowid()

    def get_by_id(self, tag_id: int) -> Optional[TagRecord]:
        row = self._conn.fetchone("SELECT * FROM tags WHERE id=?", (tag_id,))
        return self._row_to_tag(row) if row else None

    def list_by_repo(self, repo_id: int) -> list[TagRecord]:
        """列出某仓库所有标签。"""
        rows = self._conn.fetchall(
            "SELECT * FROM tags WHERE repo_id=? ORDER BY created_at DESC",
            (repo_id,),
        )
        return [self._row_to_tag(r) for r in rows]

    def list_by_snapshot(self, snapshot_id: int) -> list[TagRecord]:
        """列出某快照上的所有标签。"""
        rows = self._conn.fetchall(
            "SELECT * FROM tags WHERE snapshot_id=? ORDER BY name",
            (snapshot_id,),
        )
        return [self._row_to_tag(r) for r in rows]

    def update(
        self,
        tag_id: int,
        name: str,
        color: str,
        description: str,
    ) -> None:
        """更新标签信息。"""
        self._conn.execute(
            "UPDATE tags SET name=?, color=?, description=? WHERE id=?",
            (name, color, description, tag_id),
            commit=True,
        )

    def delete(self, tag_id: int) -> None:
        self._conn.execute("DELETE FROM tags WHERE id=?", (tag_id,), commit=True)

    @staticmethod
    def _row_to_tag(row) -> TagRecord:
        return TagRecord(
            id=row["id"],
            repo_id=row["repo_id"],
            snapshot_id=row["snapshot_id"],
            name=row["name"],
            color=row["color"],
            description=row["description"],
            created_at=row["created_at"],
        )


class IgnoreRuleDAO:
    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def insert(self, repo_id: int, pattern: str) -> int:
        """新增忽略规则，返回新行 id。"""
        now = int(time.time())
        self._conn.execute(
            "INSERT INTO ignore_rules(repo_id, pattern, is_active, created_at) VALUES (?,?,1,?)",
            (repo_id, pattern, now),
            commit=True,
        )
        return self._conn.last_insert_rowid()

    def list_active(self, repo_id: int) -> list[IgnoreRuleRecord]:
        """获取所有启用中的忽略规则（用于文件扫描过滤）。"""
        rows = self._conn.fetchall(
            "SELECT * FROM ignore_rules WHERE repo_id=? AND is_active=1",
            (repo_id,),
        )
        return [self._row_to_rule(r) for r in rows]

    def list_all(self, repo_id: int) -> list[IgnoreRuleRecord]:
        """获取所有忽略规则（含禁用的）。"""
        rows = self._conn.fetchall(
            "SELECT * FROM ignore_rules WHERE repo_id=? ORDER BY id",
            (repo_id,),
        )
        return [self._row_to_rule(r) for r in rows]

    def set_active(self, rule_id: int, is_active: bool) -> None:
        """启用或禁用某条规则。"""
        self._conn.execute(
            "UPDATE ignore_rules SET is_active=? WHERE id=?",
            (1 if is_active else 0, rule_id),
            commit=True,
        )

    def delete(self, rule_id: int) -> None:
        self._conn.execute(
            "DELETE FROM ignore_rules WHERE id=?", (rule_id,), commit=True
        )

    @staticmethod
    def _row_to_rule(row) -> IgnoreRuleRecord:
        return IgnoreRuleRecord(
            id=row["id"],
            repo_id=row["repo_id"],
            pattern=row["pattern"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )
