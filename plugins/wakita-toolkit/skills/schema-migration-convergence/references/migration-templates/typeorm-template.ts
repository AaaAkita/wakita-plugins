/**
 * TypeORM 迁移模板 — 幂等 schema 收敛
 * 
 * 将此文件复制到 src/migrations/ 目录，修改：
 * - 类名
 * - up/down 方法中的表名和列名
 */

import { MigrationInterface, QueryRunner } from 'typeorm';

export class AddAvatarColumn1700000000000 implements MigrationInterface {
  name = 'AddAvatarColumn1700000000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // 检查列是否存在
    const columnExists = await queryRunner.query(`
      SELECT COUNT(*) as count
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'users'
        AND column_name = 'avatar'
    `);

    if (columnExists[0].count === 0) {
      await queryRunner.query(`
        ALTER TABLE users ADD COLUMN avatar VARCHAR(255)
      `);
    }
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // 这些列由 ORM 模型定义管理，downgrade 不必要
    // 如果需要回滚，取消注释以下代码：
    // await queryRunner.query(`ALTER TABLE users DROP COLUMN avatar`);
  }
}

/**
 * 使用方法：
 * 1. 运行迁移：npm run typeorm migration:run
 * 2. 回滚迁移：npm run typeorm migration:revert
 * 3. 查看状态：npm run typeorm migration:show
 */