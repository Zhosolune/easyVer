# -*- coding: utf-8 -*-
"""
core/diff.py
差异比对引擎，采用策略模式：
  - 根据文件扩展名自动选择对比策略
  - TextDiffStrategy:   行级 unified diff（使用 difflib）
  - BinaryDiffStrategy: 字节级大小/哈希对比
  - 返回通用的 DiffResult，供 UI diff_viewer 渲染
"""

import difflib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Protocol

# 内容超过此大小（字节）时不做逐行 diff，直接展示"文件过大"提示
MAX_TEXT_DIFF_SIZE = 5 * 1024 * 1024   # 5 MB

# 视为文本文件的扩展名集合
TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json",
    ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bat", ".ps1", ".c", ".cpp", ".h", ".java", ".cs",
    ".go", ".rs", ".rb", ".php", ".sql", ".log", ".csv",
})


class DiffType(Enum):
    TEXT = auto()
    BINARY = auto()
    IDENTICAL = auto()
    ONLY_IN_NEW = auto()    # 新增文件
    ONLY_IN_OLD = auto()    # 已删除文件
    TOO_LARGE = auto()


@dataclass
class DiffLine:
    """单行差异信息，供 UI 渲染。"""
    old_lineno: Optional[int]   # None 表示该行在旧版本中不存在
    new_lineno: Optional[int]   # None 表示该行在新版本中不存在
    content: str
    tag: str                    # "equal" / "insert" / "delete" / "replace"


@dataclass
class DiffResult:
    """差异比对结果，与具体 UI 框架无关。"""
    diff_type: DiffType
    old_sha256: Optional[str] = None
    new_sha256: Optional[str] = None
    old_size: int = 0
    new_size: int = 0
    lines: list[DiffLine] = field(default_factory=list)
    summary: str = ""           # 人类可读的摘要，如 "+12 -3 行"


# ─────────────────────────────────────────
# 策略协议
# ─────────────────────────────────────────

class DiffStrategy(Protocol):
    def diff(
        self,
        old_content: Optional[bytes],
        new_content: Optional[bytes],
        old_sha256: Optional[str],
        new_sha256: Optional[str],
    ) -> DiffResult: ...


# ─────────────────────────────────────────
# 文本策略
# ─────────────────────────────────────────

class TextDiffStrategy:
    """使用 difflib 对文本文件做行级 unified diff。"""

    def diff(
        self,
        old_content: Optional[bytes],
        new_content: Optional[bytes],
        old_sha256: Optional[str] = None,
        new_sha256: Optional[str] = None,
    ) -> DiffResult:
        if old_content is None and new_content is None:
            return DiffResult(DiffType.IDENTICAL)
        if old_content is None:
            return DiffResult(DiffType.ONLY_IN_NEW, new_sha256=new_sha256, new_size=len(new_content))
        if new_content is None:
            return DiffResult(DiffType.ONLY_IN_OLD, old_sha256=old_sha256, old_size=len(old_content))
        if old_content == new_content:
            return DiffResult(DiffType.IDENTICAL, old_sha256=old_sha256, new_sha256=new_sha256)

        # 超大文件不做逐行 diff
        if len(old_content) > MAX_TEXT_DIFF_SIZE or len(new_content) > MAX_TEXT_DIFF_SIZE:
            return DiffResult(
                DiffType.TOO_LARGE,
                old_sha256=old_sha256, new_sha256=new_sha256,
                old_size=len(old_content), new_size=len(new_content),
                summary="文件过大，无法显示逐行差异",
            )

        try:
            enc_old = old_content.decode("utf-8", errors="replace")
            enc_new = new_content.decode("utf-8", errors="replace")
        except Exception:
            # 解码失败，降级为二进制比对
            return BinaryDiffStrategy().diff(old_content, new_content, old_sha256, new_sha256)

        old_lines = enc_old.splitlines(keepends=True)
        new_lines = enc_new.splitlines(keepends=True)

        diff_lines: list[DiffLine] = []
        added = deleted = 0
        old_lineno = new_lineno = 1

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    diff_lines.append(DiffLine(old_lineno + k, new_lineno + k, old_lines[i1 + k], "equal"))
                old_lineno += i2 - i1
                new_lineno += j2 - j1
            elif tag == "insert":
                for k in range(j2 - j1):
                    diff_lines.append(DiffLine(None, new_lineno + k, new_lines[j1 + k], "insert"))
                    added += 1
                new_lineno += j2 - j1
            elif tag == "delete":
                for k in range(i2 - i1):
                    diff_lines.append(DiffLine(old_lineno + k, None, old_lines[i1 + k], "delete"))
                    deleted += 1
                old_lineno += i2 - i1
            elif tag == "replace":
                for k in range(i2 - i1):
                    diff_lines.append(DiffLine(old_lineno + k, None, old_lines[i1 + k], "delete"))
                    deleted += 1
                for k in range(j2 - j1):
                    diff_lines.append(DiffLine(None, new_lineno + k, new_lines[j1 + k], "insert"))
                    added += 1
                old_lineno += i2 - i1
                new_lineno += j2 - j1

        return DiffResult(
            diff_type=DiffType.TEXT,
            old_sha256=old_sha256,
            new_sha256=new_sha256,
            old_size=len(old_content),
            new_size=len(new_content),
            lines=diff_lines,
            summary=f"+{added} -{deleted} 行",
        )


# ─────────────────────────────────────────
# 二进制策略
# ─────────────────────────────────────────

class BinaryDiffStrategy:
    """对二进制文件只做元信息对比（大小、哈希）。"""

    def diff(
        self,
        old_content: Optional[bytes],
        new_content: Optional[bytes],
        old_sha256: Optional[str] = None,
        new_sha256: Optional[str] = None,
    ) -> DiffResult:
        if old_content is None and new_content is None:
            return DiffResult(DiffType.IDENTICAL)
        if old_content is None:
            return DiffResult(DiffType.ONLY_IN_NEW, new_sha256=new_sha256, new_size=len(new_content))
        if new_content is None:
            return DiffResult(DiffType.ONLY_IN_OLD, old_sha256=old_sha256, old_size=len(old_content))
        if old_content == new_content:
            return DiffResult(DiffType.IDENTICAL, old_sha256=old_sha256, new_sha256=new_sha256)

        size_diff = len(new_content) - len(old_content)
        sign = "+" if size_diff >= 0 else ""
        return DiffResult(
            diff_type=DiffType.BINARY,
            old_sha256=old_sha256,
            new_sha256=new_sha256,
            old_size=len(old_content),
            new_size=len(new_content),
            summary=f"二进制文件变更，大小变化：{sign}{size_diff} 字节",
        )


# ─────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────

class DiffEngine:
    """根据文件扩展名自动路由到对应策略。"""

    _text_strategy = TextDiffStrategy()
    _binary_strategy = BinaryDiffStrategy()

    @classmethod
    def diff(
        cls,
        file_ext: str,
        old_content: Optional[bytes],
        new_content: Optional[bytes],
        old_sha256: Optional[str] = None,
        new_sha256: Optional[str] = None,
    ) -> DiffResult:
        """
        Args:
            file_ext: 文件扩展名（小写含点，如 ".py"）
            old_content: 旧版本内容字节，None 表示不存在
            new_content: 新版本内容字节，None 表示不存在
        """
        if file_ext in TEXT_EXTENSIONS:
            return cls._text_strategy.diff(old_content, new_content, old_sha256, new_sha256)
        else:
            return cls._binary_strategy.diff(old_content, new_content, old_sha256, new_sha256)
