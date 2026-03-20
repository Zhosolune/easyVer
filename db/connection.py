# -*- coding: utf-8 -*-
"""
db/connection.py
SQLite 连接管理器：
  - 线程安全（每线程独立连接，check_same_thread=False + threading.local）
  - WAL 模式 + NORMAL synchronous
  - 统一的 execute / fetchone / fetchall / executemany 接口
"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    管理指向同一个 SQLite 文件的多线程连接。
    每个线程通过 threading.local 持有独立的 sqlite3.Connection，
    避免跨线程共享连接导致的 "objects created in a thread can only be used in that same thread" 错误。
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._local = threading.local()

    # ------------------------------------------------------------------
    # 内部连接获取
    # ------------------------------------------------------------------
    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（不存在则创建）。"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            conn.row_factory = sqlite3.Row          # 结果以字典方式访问
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -8192")  # 8 MB 页缓存
            self._local.conn = conn
            logger.debug("Created new SQLite connection for thread %s", threading.current_thread().name)
        return self._local.conn

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------
    def execute(
        self,
        sql: str,
        params: Sequence[Any] = (),
        *,
        commit: bool = False,
    ) -> sqlite3.Cursor:
        """执行单条 SQL，可选是否立即提交。"""
        conn = self._get_conn()
        cursor = conn.execute(sql, params)
        if commit:
            conn.commit()
        return cursor

    def executemany(
        self,
        sql: str,
        params_seq: Sequence[Sequence[Any]],
        *,
        commit: bool = False,
    ) -> sqlite3.Cursor:
        """批量执行 SQL。"""
        conn = self._get_conn()
        cursor = conn.executemany(sql, params_seq)
        if commit:
            conn.commit()
        return cursor

    def executescript(self, script: str) -> None:
        """执行多条 SQL（用于迁移脚本）。"""
        conn = self._get_conn()
        conn.executescript(script)
        conn.commit()

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        """查询单条记录。"""
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """查询多条记录。"""
        return self.execute(sql, params).fetchall()

    def commit(self) -> None:
        """手动提交当前线程的事务。"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.commit()

    def rollback(self) -> None:
        """回滚当前线程的事务。"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.rollback()

    def close(self) -> None:
        """关闭当前线程的连接。"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            logger.debug("Closed SQLite connection for thread %s", threading.current_thread().name)

    def last_insert_rowid(self) -> int:
        """获取最后一次 INSERT 的行 ID。"""
        row = self.fetchone("SELECT last_insert_rowid()")
        return row[0] if row else -1

    @property
    def db_path(self) -> Path:
        return self._db_path
