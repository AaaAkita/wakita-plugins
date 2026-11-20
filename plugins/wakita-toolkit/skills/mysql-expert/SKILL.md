---
name: mysql-expert
description: >
  MySQL 表设计、索引、查询优化、事务与锁、迁移及 ORM 使用规范；
  含 EXPLAIN、N+1、深分页、死锁、连接池、SQL 注入防护。
when_to_use: >
  MySQL、建表、字段类型、索引、联合索引、覆盖索引、最左前缀、字符集、utf8mb4、
  慢查询、EXPLAIN、N+1、深分页、COUNT 优化、事务、隔离级别、死锁、锁等待、长事务、
  连接池、参数化查询、Alembic、Prisma Migrate、大表迁移、在线 DDL。
---

# MySQL 领域专家技能 (MySQL Expert Skill)

目标：让 MySQL 使用具备**正确性、可维护性、可观测性**，而不是只把 SQL 写通。

**适用边界**：MySQL 5.7 / 8.0（含 MariaDB 大部分语法）。PostgreSQL/Oracle 的类型、索引、
事务语义不同，不套用本 skill 的 DDL 结论。

## 一、表设计

### 类型选择

| 场景 | 推荐 | 避免 |
|------|------|------|
| 主键 | `BIGINT UNSIGNED AUTO_INCREMENT` 或雪花 ID | 随机 UUID 作聚簇主键（页分裂、写入放大） |
| 金额 | `DECIMAL(18,2)` / 最小货币单位整数 | `FLOAT`/`DOUBLE` |
| 布尔 | `TINYINT(1)` + 明确默认值 | 用字符串 `"true"/"false"` |
| 时间 | `DATETIME(3)` 或 `TIMESTAMP`（明确时区策略） | 字符串存时间 |
| 枚举 | `TINYINT` + 代码映射，或 `VARCHAR` + 校验 | MySQL `ENUM`（改值要 DDL） |
| 长文本 | `TEXT`/`MEDIUMTEXT`，必要时拆表 | 大字段与高频查询列混在一张表 |
| JSON | 仅存结构不固定、不参与高频过滤的数据 | 把核心业务字段塞进 JSON |

### 约束与约定

- 字符集统一 `utf8mb4`；MySQL 8.0 默认 `utf8mb4_0900_ai_ci`，5.7 用 `utf8mb4_general_ci`。
- 每张表有明确主键；业务唯一性用唯一索引兜底，不只靠应用层查重。
- 软删除（`deleted_at`）与唯一索引冲突：用「删除时间 + 业务键」的联合唯一索引，或归档表。
- 时间字段统一：`created_at` / `updated_at` 由数据库或统一 ORM 钩子维护，不靠每个调用方手写。
- 大字段（正文、JSON、二进制）与高频列表查询列分表或至少分页时排除。

## 二、索引设计

### 规则

1. **最左前缀**：联合索引 `(a, b, c)` 能服务 `a`、`(a,b)`、`(a,b,c)`，不能单独服务 `b`。
2. **联合索引顺序**：等值条件在前，范围条件在后；高区分度列优先。
3. **覆盖索引**：查询列全部在索引中时避免回表；`EXPLAIN` 的 `Extra` 出现 `Using index`。
4. **避免失效**：索引列上做函数、隐式类型转换、`LIKE '%x'`、`OR` 混合非索引列都会失效。
5. **控制数量**：每个索引都增加写入成本；定期清理未被使用的索引。
6. **低区分度列单独建索引价值低**（如性别、状态只有 2-3 个值），应与高区分度列组成联合索引。
7. **前缀索引**：长字符串可用 `col(20)`，但要评估区分度是否足够。

### 验证

```sql
EXPLAIN ANALYZE SELECT ...;   -- MySQL 8.0.18+
SHOW INDEX FROM <表>;
SELECT * FROM sys.schema_unused_indexes;  -- 需开启 performance_schema
```

## 三、查询优化

### EXPLAIN 判读

| 列 | 关注点 |
|----|--------|
| `type` | `const`/`eq_ref`/`ref` 较好；`range` 可接受；`index`/`ALL` 需警惕 |
| `key` | 实际使用的索引；为 NULL 说明未走索引 |
| `rows` | 预估扫描行数；远大于返回行数说明索引不理想 |
| `filtered` | 过滤比例；很低说明大量行被扫描后丢弃 |
| `Extra` | `Using index` 好；`Using filesort`/`Using temporary` 需评估 |

### 常见问题

- **N+1**：循环里查关联表。用 `joinedload`/`include`/批量 `IN` 查询解决。
- **深分页**：`LIMIT 100000, 20` 会扫描并丢弃前 10 万行。改用游标分页
  （`WHERE id > :last_id ORDER BY id LIMIT 20`）或延迟关联。
- **`COUNT(*)` 大表**：确需精确计数时接受成本；列表页优先用「是否有下一页」判断，
  不要每次都 `COUNT(*)`。
- **`SELECT *`**：增加网络与回表成本，且会因加列改变结果集。只取需要的列。
- **批量写入**：单条 `INSERT` 循环改为多值 `INSERT` 或事务内批量；注意 `max_allowed_packet`。
- **大事务**：拆批提交，避免长事务持锁与 undo 膨胀。

## 四、事务与锁

### 隔离级别

- 默认 `REPEATABLE READ`；需要读到最新提交时显式用 `READ COMMITTED`，但要评估间隙锁差异。
- 明确业务是否需要可重复读；不要在不了解语义时随意改全局隔离级别。

### 死锁排查

```sql
SHOW ENGINE INNODB STATUS\G   -- 最近一次死锁详情
SELECT * FROM information_schema.innodb_trx;
SELECT * FROM performance_schema.data_locks;
```

处理顺序：

1. 读死锁日志，确认两个事务各自持有什么锁、等待什么锁。
2. 统一加锁顺序（按主键/业务键排序后再更新）。
3. 缩小事务范围：把外部调用、慢查询移出事务。
4. 必要时降低隔离级别或改用乐观锁；不要用「加重试」掩盖死锁根因。

### 锁策略

- **悲观锁**：`SELECT ... FOR UPDATE`，适合冲突频繁、必须强一致的场景；注意索引条件，否则可能锁全表。
- **乐观锁**：`version` 字段 + `UPDATE ... WHERE version = :old`，适合冲突少的场景；更新 0 行要处理冲突。
- **长事务**：监控 `information_schema.innodb_trx` 的 `trx_started`，超过阈值告警并定位。

## 五、迁移与变更

- **Schema as Code**：所有结构变更走迁移工具（Alembic / Prisma Migrate / Flyway 等），禁止手工改生产库。
- **幂等**：多对象迁移逐对象做存在性检查，能安全重跑；见 `idempotent-migration`。
- **可回滚**：写 `downgrade` 或在发布说明中写清不可回滚原因与恢复路径。
- **大表锁窗**：FULLTEXT 表 `ADD COLUMN` 可能整表 COPY；多列合并、低峰人工执行、先评估磁盘与长事务；
  见 `idempotent-migration` 的锁窗章节。
- **多轨收敛**：`create_all` + 运行时补丁 + 迁移工具并存时，收敛为迁移工具单一管理；
  见 `schema-migration-convergence`。

## 六、安全

- **参数化查询**：禁止字符串拼接 SQL；ORM 的 raw SQL 也要用绑定参数。
- **最小权限**：应用账号只授予所需库表的 `SELECT/INSERT/UPDATE/DELETE`，不给 `DROP`/`GRANT`。
- **凭据**：走环境变量/Secret Manager，禁止入库、入镜像、入日志。
- **备份**：确认 `binlog_format=ROW`、`log_bin=ON` 与定期备份；误覆盖恢复流程见 `mysql-binlog-recovery`。

## 七、排查命令速查

```sql
SHOW FULL PROCESSLIST;                    -- 当前连接与慢查询
SHOW ENGINE INNODB STATUS\G               -- 锁、死锁、事务
SHOW STATUS LIKE 'Threads_connected';     -- 连接数
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'slow_query_log%';
SELECT * FROM information_schema.innodb_trx ORDER BY trx_started;
```

- 慢查询日志：先开 `slow_query_log` + `long_query_time`，再用 `pt-query-digest` 聚合。
- 连接池耗尽：查 `Threads_connected`、应用侧池配置、是否有连接未关闭/长事务占用。

## 八、检查清单

- [ ] 主键、字符集、时间字段、金额类型明确且统一
- [ ] 高频查询有对应索引，联合索引顺序符合最左前缀
- [ ] `EXPLAIN` 无全表扫描/文件排序/临时表（或已评估可接受）
- [ ] 无 N+1、无深分页、无 `SELECT *`
- [ ] 事务范围最小，无外部调用在事务内，死锁有统一加锁顺序
- [ ] 结构变更走迁移，幂等且可回滚
- [ ] SQL 全部参数化，应用账号权限最小化
- [ ] 慢查询与连接数有监控/告警

## 九、反模式

- ❌ 用随机 UUID 作 InnoDB 聚簇主键
- ❌ 给每个查询列都单独建索引，写入成本失控
- ❌ 在索引列上做函数或隐式类型转换，然后困惑为什么没走索引
- ❌ 用 `LIMIT` 深分页扛列表页
- ❌ 长事务里调用外部 API
- ❌ 死锁只加重试，不看 `SHOW ENGINE INNODB STATUS`
- ❌ 手工改生产表结构，绕过迁移

## 十、关联 skill

- `idempotent-migration` — 多步 DDL 幂等与大表锁窗
- `schema-migration-convergence` — 多轨 schema 管理收敛
- `mysql-binlog-recovery` — 误覆盖后的 binlog 恢复
- `config-sync-guard` — 在线可编辑配置的同步守卫
