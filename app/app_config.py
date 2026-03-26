# -*- coding: utf-8 -*-
"""
app/app_config.py
统一配置管理：基于 PyQt-Fluent-Widgets 的 QConfig/qconfig 体系。

用法::

    from app.app_config import cfg, qconfig
    # 读取
    dirs = cfg.openedRepos.value   # list[str]
    # 写入（自动持久化）
    qconfig.set(cfg.logDir, "/new/path")
"""

from __future__ import annotations

import base64
from pathlib import Path

from qfluentwidgets import (
    QConfig,
    ConfigItem,
    OptionsConfigItem,
    OptionsValidator,
    ConfigSerializer,
    EnumSerializer,
    Theme,
    qconfig,
)


# ── 自定义序列化器 ─────────────────────────────────────────────────────────────

class _ListSerializer(ConfigSerializer):
    """将 list[str] 序列化为 JSON 数组。"""

    def serialize(self, value) -> list:
        return list(value) if value else []

    def deserialize(self, value) -> list:
        return list(value) if isinstance(value, list) else []


class _BytesSerializer(ConfigSerializer):
    """将 bytes / QByteArray 序列化为 base64 字符串。"""

    def serialize(self, value) -> str:
        data = bytes(value) if not isinstance(value, bytes) else value
        return base64.b64encode(data).decode("ascii")

    def deserialize(self, value) -> bytes:
        try:
            return base64.b64decode(value)
        except Exception:
            return b""


# ── 配置类定义 ─────────────────────────────────────────────────────────────────

class EasyVerConfig(QConfig):
    """EasyVer 应用配置（继承自 QConfig，由 qconfig 统一管理持久化）。

    持久化文件：``~/.easyver/config.json``
    """

    # 仓库记忆 ─────────────────────────────────────────────────────────────────
    openedRepos = ConfigItem(
        "Repos", "Opened", [],
        serializer=_ListSerializer(),
    )
    recentRepos = ConfigItem(
        "Repos", "Recents", [],
        serializer=_ListSerializer(),
    )

    # 日志目录 ─────────────────────────────────────────────────────────────────
    logDir = ConfigItem(
        "System", "LogDir",
        str(Path.home() / ".easyver" / "logs"),
    )

    # 界面缩放 ─────────────────────────────────────────────────────────────────
    dpiScale = OptionsConfigItem(
        "Interface", "DpiScale", "Auto",
        validator=OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True
    )

    # 



# ── 单例与加载 ─────────────────────────────────────────────────────────────────

cfg = EasyVerConfig()

cfg.themeMode.value = Theme.AUTO
_CONFIG_PATH = Path.home() / ".easyver" / "config.json"
qconfig.load(str(_CONFIG_PATH), cfg)


# ── 仓库操作便捷函数 ───────────────────────────────────────────────────────────

def saved_repos() -> list[str]:
    """返回上次会话所有已打开仓库的路径列表。"""
    return list(cfg.openedRepos.value)


def save_repos(paths: list[str]) -> None:
    """覆盖写入已打开仓库列表。"""
    qconfig.set(cfg.openedRepos, list(paths))


def add_repo(path: str) -> None:
    """将仓库路径加入已打开列表（越晚打开/创建的越靠下）。"""
    repos: list[str] = list(cfg.openedRepos.value)
    if path not in repos:
        repos.append(path)
    qconfig.set(cfg.openedRepos, repos)


def remove_repo(path: str) -> None:
    """从已打开列表中移除指定仓库。"""
    repos: list[str] = list(cfg.openedRepos.value)
    if path in repos:
        repos.remove(path)
        qconfig.set(cfg.openedRepos, repos)


def recent_repos() -> list[str]:
    """返回最近访问仓库列表（最多 8 条）。"""
    return list(cfg.recentRepos.value)


def push_recent(path: str) -> None:
    """将仓库路径推入最近访问列表顶部（最多保留 8 条）。"""
    recents: list[str] = list(cfg.recentRepos.value)
    if path in recents:
        recents.remove(path)
    recents.insert(0, path)
    qconfig.set(cfg.recentRepos, recents[:8])


def remove_recent(path: str) -> None:
    """从最近访问列表中移除指定仓库。"""
    recents: list[str] = list(cfg.recentRepos.value)
    if path in recents:
        recents.remove(path)
        qconfig.set(cfg.recentRepos, recents)
