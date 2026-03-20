# -*- coding: utf-8 -*-
"""
core/repository.py
仓库管理服务：
  - 创建新仓库（初始化 .easyver 目录 + DB）
  - 打开已有仓库
  - 列出所有已注册仓库
"""

import logging
import socket
from pathlib import Path
from typing import Optional

from db.connection import DatabaseConnection
from db.migrator import run_migrations
from db.repositories.repo_dao import RepoDAO, RepoRecord

logger = logging.getLogger(__name__)

EASYVER_DIR = ".easyver"
DB_FILENAME = "easyver.db"
OBJECTS_DIRNAME = "objects"


class RepositoryService:
    """
    管理仓库的生命周期：创建、打开、删除、列出。
    每个仓库对应一个独立的 .easyver/ 目录（含独立 SQLite DB）。
    """

    def __init__(self, app_db_conn: DatabaseConnection) -> None:
        """
        Args:
            app_db_conn: 应用级全局数据库连接（存储仓库注册信息）。
        """
        self._conn = app_db_conn
        self._repo_dao = RepoDAO(app_db_conn)

    # ------------------------------------------------------------------
    # 仓库生命周期
    # ------------------------------------------------------------------
    def create(
        self,
        root_path: str | Path,
        name: str,
        description: str = "",
    ) -> RepoRecord:
        """
        在指定目录下初始化一个新仓库。
        若该目录已有 .easyver/ 则抛出 FileExistsError。
        """
        root = Path(root_path).resolve()
        easyver_dir = root / EASYVER_DIR

        if easyver_dir.exists():
            raise FileExistsError(f"仓库已存在于：{root}")

        # 创建仓库目录结构
        (easyver_dir / OBJECTS_DIRNAME).mkdir(parents=True)
        logger.info("Initialized .easyver directory at %s", easyver_dir)

        # 初始化仓库级数据库
        import time
        repo_db_path = easyver_dir / DB_FILENAME
        repo_conn = DatabaseConnection(repo_db_path)
        run_migrations(repo_conn)
        # 向仓库级 DB 的 repositories 表写入自身记录（固定 id=1）
        # 这是必要的：snapshots.repo_id FK 指向该表，不插入则提交时报 FOREIGN KEY 错误
        now = int(time.time())
        repo_conn.execute(
            """
            INSERT OR IGNORE INTO repositories
                (id, name, root_path, description, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (name, str(root), description, now, now),
            commit=True,
        )
        repo_conn.close()

        # 注册到应用级 DB
        repo_id = self._repo_dao.insert(name, str(root), description)
        record = self._repo_dao.get_by_id(repo_id)
        assert record is not None
        logger.info("Created repository '%s' at %s", name, root)
        return record

    def open(self, root_path: str | Path) -> tuple[RepoRecord, DatabaseConnection]:
        """
        打开已有仓库，返回 (RepoRecord, 仓库级DB连接)。
        若不存在则抛出 FileNotFoundError。
        """
        root = Path(root_path).resolve()
        logger.info("Opening repository at %s", root)
        easyver_dir = root / EASYVER_DIR
        db_path = easyver_dir / DB_FILENAME

        if not db_path.exists():
            logger.error("Repository not found at %s", root)
            raise FileNotFoundError(f"未找到 EasyVer 仓库：{root}")

        record = self._repo_dao.get_by_path(str(root))
        if record is None:
            # 目录存在但应用 DB 未注册（可能是移动过来的仓库），自动注册
            repo_id = self._repo_dao.insert(root.name, str(root))
            record = self._repo_dao.get_by_id(repo_id)

        repo_conn = DatabaseConnection(db_path)
        run_migrations(repo_conn)   # 确保 schema 最新
        # 确保仓库级 DB 的 repositories 表内 id=1 存在
        import time
        now = int(time.time())
        repo_conn.execute(
            """
            INSERT OR IGNORE INTO repositories
                (id, name, root_path, description, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (record.name, str(root), record.description, now, now),
            commit=True,
        )
        self._repo_dao.touch_updated_at(record.id)
        return record, repo_conn

    def list_all(self) -> list[RepoRecord]:
        """列出所有已注册的仓库。"""
        return self._repo_dao.list_all()

    def delete(self, repo_id: int) -> None:
        """从注册表中移除仓库（不删除磁盘文件）。"""
        logger.info("Removing repository ID %s from registry", repo_id)
        self._repo_dao.delete(repo_id)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def get_objects_dir(root_path: str | Path) -> Path:
        """获取仓库对象存储目录路径。"""
        return Path(root_path) / EASYVER_DIR / OBJECTS_DIRNAME

    @staticmethod
    def get_db_path(root_path: str | Path) -> Path:
        """获取仓库 SQLite 数据库路径。"""
        return Path(root_path) / EASYVER_DIR / DB_FILENAME

    @staticmethod
    def current_author() -> str:
        """生成提交者标识（用户名@主机名）。"""
        import getpass
        try:
            user = getpass.getuser()
        except Exception:
            user = "unknown"
        return f"{user}@{socket.gethostname()}"
