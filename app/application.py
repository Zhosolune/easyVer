# -*- coding: utf-8 -*-
"""
v2/app/application.py
多仓库全局单例：
  - 维护所有已打开仓库的 {path → (RepoRecord, DatabaseConnection)} 映射
  - 启动时自动恢复上次会话的仓库
"""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from db.connection import DatabaseConnection
from db.migrator import run_migrations
from core.repository import RepositoryService
from db.repositories.repo_dao import RepoRecord
from app.app_config import add_repo, remove_repo, push_recent, saved_repos, remove_recent


class EasyVerApp:
    """全局单例，管理多仓库状态。"""

    _instance: EasyVerApp | None = None

    # app-level 全局注册 DB（记录仓库列表）
    _APP_DB_PATH = Path.home() / ".easyver_v2" / "app.db"

    def __init__(self) -> None:
        EasyVerApp._instance = self

        # 初始化全局 DB
        self._APP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._app_conn = DatabaseConnection(self._APP_DB_PATH)
        run_migrations(self._app_conn)
        self.repo_service = RepositoryService(self._app_conn)

        # {root_path: (RepoRecord, DatabaseConnection)}
        self._open_repos: dict[str, tuple[RepoRecord, DatabaseConnection]] = {}

    # ------------------------------------------------------------------
    # 仓库生命周期
    # ------------------------------------------------------------------
    def create_repo(self, root_path: str, name: str, desc: str = "") -> RepoRecord:
        """新建仓库并加入已打开列表。"""
        record = self.repo_service.create(root_path, name, desc)
        record, conn = self.repo_service.open(root_path)
        self._open_repos[str(Path(root_path).resolve())] = (record, conn)
        add_repo(str(Path(root_path).resolve()))
        push_recent(str(Path(root_path).resolve()))
        return record

    def open_repo(self, root_path: str) -> RepoRecord:
        """打开仓库（已打开则直接返回）。"""
        key = str(Path(root_path).resolve())
        if key in self._open_repos:
            return self._open_repos[key][0]
        record, conn = self.repo_service.open(root_path)
        self._open_repos[key] = (record, conn)
        add_repo(key)
        push_recent(key)
        return record

    def close_repo(self, root_path: str) -> None:
        """关闭并从会话中移除仓库（不删除文件）。"""
        key = str(Path(root_path).resolve())
        if key in self._open_repos:
            _, conn = self._open_repos.pop(key)
            conn.close()
        remove_repo(key)

    def delete_repo(self, root_path: str) -> None:
        """从应用中彻底删除仓库记录。"""
        key = str(Path(root_path).resolve())
        record = self.get_record(root_path)
        if record:
            self.repo_service.delete(record.id)
        self.close_repo(root_path)
        remove_recent(key)

    def restore_last_session(self) -> list[str]:
        """
        恢复上次会话的所有仓库，返回成功打开的路径列表。
        跳过不存在或已损坏的仓库。
        """
        opened: list[str] = []
        for path in saved_repos():
            try:
                self.open_repo(path)
                opened.append(path)
            except Exception:
                remove_repo(path)  # 自动清理失效记录
        return opened

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------
    def opened_repos(self) -> list[RepoRecord]:
        return [record for record, _ in self._open_repos.values()]

    def get_record(self, root_path: str) -> RepoRecord | None:
        key = str(Path(root_path).resolve())
        entry = self._open_repos.get(key)
        return entry[0] if entry else None

    def get_conn(self, root_path: str) -> DatabaseConnection | None:
        key = str(Path(root_path).resolve())
        entry = self._open_repos.get(key)
        return entry[1] if entry else None

    # ------------------------------------------------------------------
    # 关闭
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        for key, (_, conn) in list(self._open_repos.items()):
            conn.close()
        self._app_conn.close()
