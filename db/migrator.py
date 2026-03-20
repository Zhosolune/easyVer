# -*- coding: utf-8 -*-
"""
db/migrator.py
数据库迁移执行器：
  - 扫描 migrations/ 目录下的 *.sql 文件（按文件名升序）
  - 对照 schema_version 表，只执行尚未应用的版本
  - 整体幂等，可重复运行
"""

import logging
import re
from pathlib import Path

from db.connection import DatabaseConnection

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_VERSION_RE = re.compile(r"^(\d+)_.*\.sql$")


def _parse_version(filename: str) -> int | None:
    """从文件名中提取版本号，如 '001_init.sql' → 1。"""
    m = _VERSION_RE.match(filename)
    return int(m.group(1)) if m else None


def run_migrations(conn: DatabaseConnection) -> None:
    """
    对 conn 指向的数据库执行所有未应用的迁移脚本。
    应在程序启动、数据库连接建立后立即调用。
    """
    # 确保版本表存在（首次运行时 schema_version 还不存在）
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            applied_at  INTEGER NOT NULL,
            description TEXT    NOT NULL DEFAULT ''
        )
        """,
        commit=True,
    )

    applied: set[int] = {
        row["version"] for row in conn.fetchall("SELECT version FROM schema_version")
    }

    migration_files = sorted(
        f for f in _MIGRATIONS_DIR.iterdir()
        if f.is_file() and f.suffix == ".sql"
    )

    for sql_file in migration_files:
        version = _parse_version(sql_file.name)
        if version is None or version in applied:
            continue

        logger.info("Applying migration v%03d: %s", version, sql_file.name)
        script = sql_file.read_text(encoding="utf-8")
        try:
            conn.executescript(script)
        except Exception as exc:
            logger.error("Migration v%03d failed: %s", version, exc)
            raise

        logger.info("Migration v%03d applied successfully.", version)
