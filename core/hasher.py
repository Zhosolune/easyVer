# -*- coding: utf-8 -*-
"""
core/hasher.py
分块 SHA-256 哈希计算工具：
  - 支持大文件（流式分块读取，默认 4 MB/块）
  - 提供文件哈希 + 字节串哈希两个接口
"""

import hashlib
from pathlib import Path

# 分块大小（字节）：4 MB，在内存占用与 I/O 次数之间取得平衡
CHUNK_SIZE: int = 4 * 1024 * 1024


def hash_file(path: str | Path, chunk_size: int = CHUNK_SIZE) -> str:
    """
    计算文件的 SHA-256 哈希值。

    Args:
        path: 文件路径
        chunk_size: 每次读取的字节数（默认 4 MB）

    Returns:
        64 位十六进制字符串，如 "a3b1c2..."
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_bytes(data: bytes) -> str:
    """计算字节串的 SHA-256 哈希值。"""
    return hashlib.sha256(data).hexdigest()


def object_relative_path(sha256: str) -> str:
    """
    将 SHA-256 哈希映射为对象存储的相对路径。
    使用前两位作为子目录，避免单目录文件过多。

    e.g. "ab3f1c..." → "ab/3f1c..."
    """
    return f"{sha256[:2]}/{sha256[2:]}"
