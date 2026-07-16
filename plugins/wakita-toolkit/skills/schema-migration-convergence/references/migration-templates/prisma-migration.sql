-- Prisma 迁移模板 — 幂等 schema 收敛
-- 将此文件内容添加到 Prisma migration 的 migration.sql 中
-- 或在自定义脚本中使用

-- 助手函数：检查列是否存在（MySQL）
-- 注意：MySQL 不支持 IF NOT EXISTS 语法，需要用存储过程或在应用层探测

-- 方法 1：使用 Prisma 的 $executeRaw（在 TypeScript 中）
-- await prisma.$executeRaw`
--   SELECT COUNT(*) INTO @exists
--   FROM information_schema.columns
--   WHERE table_schema = DATABASE()
--     AND table_name = 'users'
--     AND column_name = 'avatar';
--   IF @exists = 0 THEN
--     ALTER TABLE users ADD COLUMN avatar VARCHAR(255);
--   END IF;
-- `

-- 方法 2：直接添加列（如果确定列不存在）
-- ALTER TABLE users ADD COLUMN avatar VARCHAR(255);

-- 方法 3：使用 Prisma 的 @add directive（在 schema.prisma 中）
-- model User {
--   id      Int    @id @default(autoincrement())
--   name    String
--   avatar  String?  // 新增的可选字段
-- }

-- 然后运行：npx prisma migrate dev --name add_avatar_column

-- =====================================================
-- 以下为实际迁移 SQL 模板
-- =====================================================

-- ADD 列模板
-- ALTER TABLE table_name ADD COLUMN column_name column_type;

-- DROP 列模板
-- ALTER TABLE table_name DROP COLUMN column_name;

-- 修改列类型模板
-- ALTER TABLE table_name MODIFY COLUMN column_name new_column_type;