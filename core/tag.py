# -*- coding: utf-8 -*-
"""
core/tag.py
标签管理服务。
"""

from db.connection import DatabaseConnection
from db.repositories.tag_dao import TagDAO, TagRecord
import logging

logger = logging.getLogger(__name__)

class TagService:
    def __init__(self, repo_id: int, repo_conn: DatabaseConnection) -> None:
        self._repo_id = repo_id
        self._dao = TagDAO(repo_conn)

    def create(
        self,
        snapshot_id: int,
        name: str,
        color: str = "#5B9BD5",
        description: str = "",
    ) -> TagRecord:
        """新建标签，返回 TagRecord。"""
        tag_id = self._dao.insert(self._repo_id, snapshot_id, name, color, description)
        logger.info("Created tag #%s '%s' for snapshot #%d", tag_id, name, snapshot_id)
        return self._dao.get_by_id(tag_id)

    def list_by_repo(self) -> list[TagRecord]:
        return self._dao.list_by_repo(self._repo_id)

    def list_by_snapshot(self, snapshot_id: int) -> list[TagRecord]:
        return self._dao.list_by_snapshot(snapshot_id)

    def update(self, tag_id: int, name: str, color: str, description: str) -> None:
        logger.info("Updating tag #%s to '%s'", tag_id, name)
        self._dao.update(tag_id, name, color, description)

    def delete(self, tag_id: int) -> None:
        logger.info("Deleting tag #%s", tag_id)
        self._dao.delete(tag_id)
