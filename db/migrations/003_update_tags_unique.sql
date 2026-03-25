-- ============================================================
-- EasyVer 数据库迁移脚本 v003
-- 修改 tags 表，移除 UNIQUE(repo_id, name) 约束，改为 UNIQUE(snapshot_id, name)
-- 以允许不同快照使用同名标签（类似于分类/Label）。
-- ============================================================

CREATE TABLE IF NOT EXISTS tags_new (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id     INTEGER NOT NULL
                    REFERENCES repositories(id) ON DELETE CASCADE,
    snapshot_id INTEGER NOT NULL
                    REFERENCES snapshots(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,                     -- 标签名（如 "重要"、"bugfix"）
    color       TEXT    NOT NULL DEFAULT '#5B9BD5',   -- 显示颜色（十六进制 RGB）
    description TEXT    NOT NULL DEFAULT '',           -- 标签描述
    created_at  INTEGER NOT NULL,                     -- 创建时间（Unix 时间戳，秒）
    UNIQUE(snapshot_id, name)                         -- 同一个快照内标签名唯一
);

INSERT INTO tags_new (id, repo_id, snapshot_id, name, color, description, created_at)
SELECT id, repo_id, snapshot_id, name, color, description, created_at FROM tags;

DROP TABLE tags;

ALTER TABLE tags_new RENAME TO tags;

CREATE INDEX IF NOT EXISTS idx_tags_snapshot ON tags(snapshot_id);

INSERT OR IGNORE INTO schema_version(version, applied_at, description)
VALUES (3, strftime('%s','now'), 'Change tags unique constraint to snapshot_id and name');
