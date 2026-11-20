---
name: idempotent-migration
description: >
  多步 DDL 迁移的幂等守卫与验收：中断重跑、部分应用、Duplicate column、
  大表锁窗与部署时序。
when_to_use: >
  写迁移、migration、ADD COLUMN、CREATE INDEX、Duplicate column、迁移中断、部分应用、
  非事务 DDL、idempotent migration、大表迁移、锁窗、FULLTEXT、迁移很慢、部署卡在迁移。
---

# 幂等迁移守卫

**适用边界**：以 MySQL + Alembic 为主，DDL 隐式提交/不可回滚、FULLTEXT 大表 COPY 等结论是 MySQL 特性。
PostgreSQL 的 DDL 可在事务内回滚，`ADD COLUMN` 的锁行为也不同，不要直接套用；Prisma/Django/TypeORM
的写法对照见 `schema-migration-convergence`。

## 为什么：半个迁移的真实成因

MySQL（以及若干其他数据库）的 DDL 隐式提交、不可回滚。一个含多步 DDL 的迁移
被外部因素中断——部署健康检查超时杀容器、OOM、连接断开——已经执行的语句留在库里，
版本戳却没推进。下次部署重跑整个迁移，第一条撞见已存在对象就报错
（1060 Duplicate column / 1050 Table exists），启动失败，自动回滚，再部署再失败，死循环。

实战案例（2026-08-31）：迁移第一条 `ADD COLUMN` 完成后容器被杀，生产库遗留未登记的列；
后续每次部署都撞 1060 回滚。修复方式就是把迁移改为幂等。

## 规则

**迁移含 ≥2 个 DDL 对象时，每个对象分别做存在性检查再创建。** 单对象迁移不需要
（失败即整体未应用，重跑安全）。alembic 写法：

```python
def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)  # Inspector 无状态，每次调用现查 information_schema

    cols = {c["name"] for c in insp.get_columns("crawled_data")}
    if "platform_content_id" not in cols:
        op.add_column("crawled_data", sa.Column("platform_content_id", ...))

    idx = {i["name"] for i in insp.get_indexes("crawled_data")}
    if "ix_crawled_data_platform_content_id" not in idx:
        op.create_index(...)

    if not insp.has_table("crawler_comments"):
        op.create_table(...)  # PK/UniqueConstraint 随表一次创建，无需单独守卫

    # 表与索引分开守卫：覆盖"表已建但索引未建"的中断位置
    t_idx = {i["name"] for i in insp.get_indexes("crawler_comments")}
    for name, cols in [("ix_a", ["a"]), ("ix_b", ["b"])]:
        if name not in t_idx:
            op.create_index(name, "crawler_comments", cols, unique=False)
```

注意点：

- 守卫的是**对象粒度**（列、索引、表各自独立），对应各种可能的中断位置
- 终态 schema 必须与不中断的执行路径**完全一致**（类型/默认值/注释/索引名/约束名），
  不能为省事简化对象定义
- 这不是"运行时 schema 补丁"——守卫在迁移文件里，仍由迁移工具唯一管理，
  与 schema-migration-convergence 的约束不冲突
- 已在版本戳上的环境不受影响：alembic 按版本戳跳过该 revision，文件内容变化不触发重跑

## 大表锁窗与迁移时序

幂等只保证「重跑不炸」，不代表「迁移很便宜」。大表 DDL 的锁窗和部署时机会直接决定事故范围。

### 大表 ADD COLUMN 的真实代价

- 带 **FULLTEXT 索引**的表在 MySQL 8.0 下 `ADD COLUMN` **不能走 INSTANT**，
  每次加列都是整表 COPY（报 1846），并长时间持 MDL。实测：几万行 / 几百 MB 的表，
  单列耗时可达十几到几十分钟。
- 该 COPY 过程通常是**单线程**的，加 CPU 配额收益在 1 核附近就饱和；
  它**阻塞写、不阻塞读**（迁移期间 `SELECT COUNT(*)` 正常）。
- 多列尽量合并为**一条** `ALTER TABLE ... ADD COLUMN a, ADD COLUMN b`；
  但独立的 `ADD INDEX` 可以走 INPLACE，所以「加列 + 加索引」拆成
  `add_column` + `create_index` 两步也只需一次整表重建。
- `ALTER COLUMN ... DROP DEFAULT` 可走 INSTANT，适合「加列带默认值 → 回填 → 去默认值」。

### 估算与验证

- **不要用本地小表估生产窗口**：表大小、CPU 配额、单线程特性都会让估算失真。
- 正确性用探测表验证：`CREATE TABLE probe LIKE big_table` + 灌几百行 + 单独版本戳，
  几分钟验证列/索引/回填/downgrade/重入幂等；大表迁移让它后台跑完即可。

### 部署时序

- CD 常见顺序是：记录上一版本 SHA → **执行迁移（此时旧服务仍在线）** →
  重建/启动新容器 → 健康检查 → 失败回滚。
- 部署超时被杀可能**不走回滚**，停在「迁移已完成、新代码未启动」的半途。
- 大表迁移（含 `ADD COLUMN`、大表 `ALTER`）必须人工低峰执行：
  停 worker/定时任务 → 确认无长事务 → 磁盘余量 ≥2× → 跑迁移 → 验证 → 恢复服务。
- 不要指望 CI 健康检查兜住锁窗；锁窗期间接口 500/写入失败不是新代码 bug。

## 回滚审查（被 clean-home 的数据/部署步骤加载时）

- 迁移是否有 down/回滚路径？只 forward、不可逆 → P0。
- 配置变更（env/compose/nginx）是否可回滚？没有旧值备份或回滚脚本 → P0。
- 不可回滚时，是否至少有人工恢复步骤和验证方法？没有 → 记「证据缺失」。

## 验收方法（合并前必做）

1. **部分应用路径**：测试库升到目标迁移的前一版本，手动执行目标迁移的**第一条 DDL**
   （模拟中断现场），然后 `upgrade head`——必须成功且版本戳推进
2. **全新路径**：空库直接 `upgrade head`——必须成功
3. **终态比对**：两条路径的 `SHOW CREATE TABLE` 与一个"从未中断"的参照库逐字 diff
   （去掉 `AUTO_INCREMENT=` 等随数据变化的项），必须零差异
