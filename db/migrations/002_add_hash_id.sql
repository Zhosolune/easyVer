-- ============================================================
-- EasyVer 数据库迁移脚本 v002
-- 新增：为每个里程碑增加 8 位的唯一哈希值 hash_id
-- ============================================================

ALTER TABLE snapshots ADD COLUMN hash_id TEXT NOT NULL DEFAULT '';
UPDATE snapshots SET hash_id = substr(lower(hex(randomblob(4))), 1, 8) WHERE hash_id = '';

INSERT OR IGNORE INTO schema_version(version, applied_at, description)
VALUES (2, strftime('%s','now'), 'Add hash_id to snapshots');
