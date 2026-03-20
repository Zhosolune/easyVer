-- ============================================================
-- EasyVer 数据库初始化迁移脚本 v001
-- 执行顺序：connection.py 在首次连接时自动调用 migrator.py
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;   -- WAL 模式下 NORMAL 已足够安全


-- ============================================================
-- Table: repositories   仓库元信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS repositories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,                    -- 用户自定义仓库名称
    root_path   TEXT    NOT NULL UNIQUE,             -- 仓库根目录绝对路径（OS 原生路径）
    description TEXT    NOT NULL DEFAULT '',         -- 仓库描述
    created_at  INTEGER NOT NULL,                    -- 创建时间（Unix 时间戳，秒）
    updated_at  INTEGER NOT NULL                     -- 最后操作时间（Unix 时间戳，秒）
);


-- ============================================================
-- Table: snapshots   快照（版本）表
-- ============================================================
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id     INTEGER NOT NULL
                    REFERENCES repositories(id) ON DELETE CASCADE,
    parent_id   INTEGER
                    REFERENCES snapshots(id),        -- 父快照 ID；NULL = 首次提交
    name        TEXT    NOT NULL DEFAULT '',          -- 里程碑名称
    summary     TEXT    NOT NULL DEFAULT '',          -- 摘要
    detail      TEXT    NOT NULL DEFAULT '',          -- 详细说明
    author      TEXT    NOT NULL DEFAULT '',          -- 提交者（用户名 / 主机名）
    total_files INTEGER NOT NULL DEFAULT 0,           -- 本次归档的文件总数
    total_size  INTEGER NOT NULL DEFAULT 0,           -- 所有文件原始字节数之和
    created_at  INTEGER NOT NULL                      -- 提交时间（Unix 时间戳，秒）
);

CREATE INDEX IF NOT EXISTS idx_snapshots_repo
    ON snapshots(repo_id, created_at DESC);


-- ============================================================
-- Table: blobs   内容对象表（内容寻址去重存储）
-- ============================================================
CREATE TABLE IF NOT EXISTS blobs (
    sha256          TEXT    PRIMARY KEY,              -- 文件内容 SHA-256（64 位十六进制）
    size_original   INTEGER NOT NULL,                 -- 原始文件字节数
    size_compressed INTEGER NOT NULL,                 -- zstd 压缩后字节数
    object_path     TEXT    NOT NULL,                 -- 相对于 .easyver/objects/ 的存储路径
    ref_count       INTEGER NOT NULL DEFAULT 0,       -- 引用计数（GC 依据）
    created_at      INTEGER NOT NULL                  -- 首次写入时间（Unix 时间戳，秒）
);


-- ============================================================
-- Table: snapshot_files   快照文件清单表
-- ============================================================
CREATE TABLE IF NOT EXISTS snapshot_files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL
                    REFERENCES snapshots(id) ON DELETE CASCADE,
    blob_sha256 TEXT    NOT NULL
                    REFERENCES blobs(sha256),
    file_path   TEXT    NOT NULL,                     -- 相对于仓库根目录的路径（正斜杠分隔）
    file_name   TEXT    NOT NULL,                     -- 文件名（冗余，用于快速过滤）
    file_ext    TEXT    NOT NULL DEFAULT '',           -- 扩展名（小写，含点，如 ".py"）
    file_size   INTEGER NOT NULL,                     -- 原始文件字节数
    modified_at INTEGER NOT NULL,                     -- 文件 mtime（Unix 时间戳，秒）
    permissions TEXT             DEFAULT NULL,         -- 文件权限（保留字段）
    status      TEXT    NOT NULL DEFAULT 'added'      -- 变更状态: added / modified / deleted / unchanged
);

CREATE INDEX IF NOT EXISTS idx_sf_snapshot
    ON snapshot_files(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_sf_blob
    ON snapshot_files(blob_sha256);
CREATE INDEX IF NOT EXISTS idx_sf_file_path
    ON snapshot_files(snapshot_id, file_path);


-- ============================================================
-- Table: tags   标签表
-- ============================================================
CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id     INTEGER NOT NULL
                    REFERENCES repositories(id) ON DELETE CASCADE,
    snapshot_id INTEGER NOT NULL
                    REFERENCES snapshots(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,                     -- 标签名（如 "v1.0"、"release-2024"）
    color       TEXT    NOT NULL DEFAULT '#5B9BD5',   -- 显示颜色（十六进制 RGB）
    description TEXT    NOT NULL DEFAULT '',           -- 标签描述
    created_at  INTEGER NOT NULL,                     -- 创建时间（Unix 时间戳，秒）
    UNIQUE(repo_id, name)                             -- 同仓库内标签名唯一
);

CREATE INDEX IF NOT EXISTS idx_tags_snapshot
    ON tags(snapshot_id);


-- ============================================================
-- Table: ignore_rules   忽略规则表（类 .gitignore）
-- ============================================================
CREATE TABLE IF NOT EXISTS ignore_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id    INTEGER NOT NULL
                   REFERENCES repositories(id) ON DELETE CASCADE,
    pattern    TEXT    NOT NULL,                      -- glob 模式，如 "*.tmp"、"node_modules/**"
    is_active  INTEGER NOT NULL DEFAULT 1,            -- 是否启用（1=启用，0=禁用）
    created_at INTEGER NOT NULL                       -- 创建时间（Unix 时间戳，秒）
);


-- ============================================================
-- Table: settings   全局 KV 配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT    PRIMARY KEY,                   -- 配置键，如 "theme"、"last_repo_id"
    value      TEXT    NOT NULL,                      -- 配置值（JSON 序列化字符串）
    updated_at INTEGER NOT NULL                       -- 最后修改时间（Unix 时间戳，秒）
);


-- ============================================================
-- Table: schema_version   迁移版本记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,                   -- 迁移版本号
    applied_at INTEGER NOT NULL,                      -- 执行时间（Unix 时间戳，秒）
    description TEXT NOT NULL DEFAULT ''              -- 本次迁移说明
);

INSERT OR IGNORE INTO schema_version(version, applied_at, description)
VALUES (1, strftime('%s','now'), 'Initial schema creation');
