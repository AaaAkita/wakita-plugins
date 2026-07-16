# 案例：数据库迁移收敛实战

本案例展示一个真实项目从「三轨并存」到「单一管理」的完整收敛过程。

---

## 问题背景

项目使用 Python + FastAPI + SQLAlchemy + Alembic，但在演进过程中积累了三套 schema 管理机制：

1. **`Base.metadata.create_all`** — 早期用来建新表
2. **运行时补丁** — 启动时 `information_schema` 探测 + `ALTER TABLE` 补齐列
3. **Alembic** — 后期引入的版本化迁移

### 问题代码

`app/database/mysql.py` 中的 `_ensure_schema_compatibility()` 函数在每次启动时执行 17 条 ALTER TABLE：

```python
async def _ensure_schema_compatibility():
    patches = {
        "crawled_data": [
            ("alerted", "ALTER TABLE crawled_data ADD COLUMN alerted BOOLEAN ..."),
            ("extra_info", "ALTER TABLE crawled_data ADD COLUMN extra_info JSON ..."),
            # ... 更多列
        ],
        "tasks": [
            ("include_words", "ALTER TABLE tasks ADD COLUMN include_words TEXT ..."),
            # ... 更多列
        ],
        "crawler_states": [
            ("active_task_id", "ALTER TABLE crawler_states DROP COLUMN active_task_id"),
            # ... 更多列
        ],
    }
    # ... 17 条 ALTER TABLE
```

`init_mysql()` 调用此函数，意味着**每次 FastAPI 启动和每个 Celery worker 启动都执行**。

### 问题影响

| 影响 | 说明 |
|------|------|
| 启动变慢 | 每次启动都要查询 information_schema |
| 变更不可追溯 | ALTER TABLE 分散在代码中，无版本管理 |
| 三套代码可能冲突 | 改一张表有三处可能动 |
| Worker 路径复杂 | Worker 只调 `init_mysql()`，补丁对 worker 是必需的 |

---

## 修复过程

### 第 1 步：创建 Alembic 迁移

将 17 条 ALTER TABLE 转为一个幂等的 Alembic 迁移版本：

```python
# alembic/versions/d5e6f7a8b9c0_converge_schema.py

def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = :table AND column_name = :col"
        ),
        {"table": table, "col": column},
    )
    return (result.scalar() or 0) > 0

def upgrade() -> None:
    conn = op.get_bind()
    
    # crawled_data: ADD 7 列
    add_patches = {
        "crawled_data": [
            ("alerted", "ALTER TABLE crawled_data ADD COLUMN alerted BOOLEAN DEFAULT FALSE"),
            ("extra_info", "ALTER TABLE crawled_data ADD COLUMN extra_info JSON"),
            ("embedding_status", "ALTER TABLE crawled_data ADD COLUMN embedding_status VARCHAR(20)"),
            # ... 其他列
        ],
        "tasks": [
            ("include_words", "ALTER TABLE tasks ADD COLUMN include_words TEXT"),
            # ... 其他列
        ],
    }
    
    for table_name, patches in add_patches.items():
        for column_name, alter_sql in patches:
            if not _column_exists(conn, table_name, column_name):
                conn.execute(text(alter_sql))
    
    # crawler_states: DROP 6 列
    drop_patches = {
        "crawler_states": [
            "active_task_id", "active_task_status", "session_crawled_count",
            "error_count", "last_error_time", "last_error_message",
        ]
    }
    
    for table_name, columns in drop_patches.items():
        for col in columns:
            if _column_exists(conn, table_name, col):
                conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {col}"))
```

### 第 2 步：删除运行时补丁

1. 删除 `_ensure_schema_compatibility()` 函数（120 行）
2. 删除 `init_mysql()` 中的调用
3. 删除不再使用的 `from sqlalchemy import text` 导入

### 第 3 步：验证

```bash
# 离线验证 SQL
alembic upgrade head --sql

# 在线执行
alembic upgrade head

# 确认到达 head
alembic current

# 代码质量
mypy app/ && pytest tests/
```

---

## 修复后状态

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| Schema 管理方式 | 3 套并存 | 仅 Alembic |
| 启动时额外查询 | 每次 information_schema 扫描 | 无 |
| mysql.py 行数 | 228 | 74 |
| 变更追溯 | 散落在代码中 | 版本化管理 |

---

## 遇到的坑

### 1. MySQL 不支持 `ADD COLUMN IF NOT EXISTS`

生产环境 MySQL 版本 < 8.0.29，只能用 information_schema 探测。

**解决方案**：在迁移脚本中用 `_column_exists()` 函数探测。

### 2. Worker 路径不同

Worker 只调 `init_mysql()`，补丁对 worker 是必需的。迁移后需要在 worker 启动前确保 `alembic upgrade head` 已执行。

**解决方案**：
- Docker Compose 中 `depends_on` 添加 `condition: service_healthy`
- Worker 启动脚本中添加 `alembic upgrade head`

### 3. downgrade 语义

这些列由 ORM `create_all` 管理，downgrade 不必手动 DROP（下次 `create_all` 会重建）。

**解决方案**：`downgrade()` 函数留空，注释说明原因。

---

## 关键经验

1. **迁移必须幂等**——用列存在性探测包裹 ALTER，确保安全重复执行
2. **Worker 路径别忘了**——迁移后 Worker 启动前也要确保迁移已执行
3. **downgrade 可以留空**——如果列由 ORM 管理，不需要手动 DROP
4. **先验证再执行**——用 `--sql` 参数离线验证生成的 SQL
5. **三轨并存是定时炸弹**——越早收敛越好