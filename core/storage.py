# -*- coding: utf-8 -*-
"""
core/storage.py
Blob 对象存储服务：
  - 基于内容寻址（SHA-256），内容相同的文件只存储一次
  - 写入时使用 zstd 压缩，读取时自动解压
  - 提供 GC 接口（配合 BlobDAO.list_orphans 使用）
"""

import logging
from pathlib import Path
from typing import Iterator

import zstandard as zstd

from core.hasher import hash_file, object_relative_path, CHUNK_SIZE
from db.connection import DatabaseConnection
from db.repositories.file_dao import BlobDAO

logger = logging.getLogger(__name__)

# zstd 压缩级别（1=最快, 22=最高压缩率, 推荐 3~6）
ZSTD_LEVEL: int = 3


class StorageService:
    """
    管理 .easyver/objects/ 目录下的 blob 文件：
      - store_file():  将源文件压缩写入对象存储，返回 sha256
      - read_bytes():  解压读取 blob 内容
      - extract_to():  将 blob 解压还原到指定目标路径
      - run_gc():      删除 ref_count=0 的孤立 blob 文件
    """

    def __init__(self, objects_dir: str | Path, conn: DatabaseConnection) -> None:
        self._objects_dir = Path(objects_dir)
        self._objects_dir.mkdir(parents=True, exist_ok=True)
        self._blob_dao = BlobDAO(conn)
        self._cctx = zstd.ZstdCompressor(level=ZSTD_LEVEL)
        self._dctx = zstd.ZstdDecompressor()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def store_file(self, src_path: str | Path) -> str:
        """
        将文件写入对象存储。
        若内容已存在（哈希相同），仅增加 ref_count，不重复写磁盘。

        Returns:
            文件内容的 SHA-256 哈希字符串。
        """
        src = Path(src_path)
        sha256 = hash_file(src)

        if self._blob_dao.exists(sha256):
            self._blob_dao.increment_ref(sha256)
            logger.debug("Blob already exists, incremented ref: %s", sha256[:8])
            return sha256

        # 首次写入：压缩并存储
        rel_path = object_relative_path(sha256)
        dest = self._objects_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        size_original = src.stat().st_size
        size_compressed = self._compress_file(src, dest)

        self._blob_dao.insert(sha256, size_original, size_compressed, rel_path)
        self._blob_dao.increment_ref(sha256)
        logger.debug(
            "Stored blob %s... (%.1f KB → %.1f KB, ratio=%.1f%%)",
            sha256[:8],
            size_original / 1024,
            size_compressed / 1024,
            100 * size_compressed / max(size_original, 1),
        )
        return sha256

    def _compress_file(self, src: Path, dest: Path) -> int:
        """流式压缩 src 写入 dest，返回压缩后字节数。"""
        with open(src, "rb") as fin, open(dest, "wb") as fout:
            with self._cctx.stream_writer(fout) as writer:
                while True:
                    chunk = fin.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    writer.write(chunk)
        return dest.stat().st_size

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    def read_bytes(self, sha256: str) -> bytes:
        """读取并解压 blob 内容，返回原始字节。"""
        blob_path = self._resolve_path(sha256)
        with open(blob_path, "rb") as f:
            # 使用 stream_reader 而非 decompress()：
            # stream_writer 写入的帧头不含内容大小，decompress() 会报错
            with self._dctx.stream_reader(f) as reader:
                return reader.read()

    def iter_chunks(self, sha256: str, chunk_size: int = CHUNK_SIZE) -> Iterator[bytes]:
        """流式读取解压后的 blob 内容（适用于大文件还原）。"""
        blob_path = self._resolve_path(sha256)
        with open(blob_path, "rb") as f:
            with self._dctx.stream_reader(f) as reader:
                while True:
                    chunk = reader.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

    def extract_to(self, sha256: str, dest_path: str | Path) -> None:
        """将 blob 解压还原到指定目标路径（目录不存在则自动创建）。"""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fout:
            for chunk in self.iter_chunks(sha256):
                fout.write(chunk)
        logger.debug("Extracted blob %s... → %s", sha256[:8], dest)

    # ------------------------------------------------------------------
    # GC（垃圾回收）
    # ------------------------------------------------------------------
    def run_gc(self) -> tuple[int, int]:
        """
        删除所有引用计数为 0 的孤立 blob。

        Returns:
            (deleted_count, freed_bytes)
        """
        orphans = self._blob_dao.list_orphans()
        deleted_count = 0
        freed_bytes = 0

        for blob in orphans:
            obj_path = self._objects_dir / blob.object_path
            if obj_path.exists():
                freed_bytes += obj_path.stat().st_size
                obj_path.unlink()
            self._blob_dao.delete(blob.sha256)
            deleted_count += 1
            logger.debug("GC deleted blob: %s", blob.sha256[:8])

        logger.info("GC complete: deleted %d blobs, freed %.2f KB", deleted_count, freed_bytes / 1024)
        return deleted_count, freed_bytes

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _resolve_path(self, sha256: str) -> Path:
        """将 sha256 转换为实际文件系统路径，文件不存在时抛出 FileNotFoundError。"""
        path = self._objects_dir / object_relative_path(sha256)
        if not path.exists():
            raise FileNotFoundError(f"Blob not found in object store: {sha256}")
        return path
