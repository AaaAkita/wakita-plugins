# 侦查模式参考

定位运行时 schema 补丁的搜索方法和常见形态。

## 通用搜索命令

```bash
# 1. information_schema 查询（列存在性探测）
grep -rn "information_schema" app/ src/ --include="*.py" --include="*.ts" --include="*.js" --include="*.go" --include="*.java"

# 2. 启动时的 ALTER TABLE 操作
grep -rn "ALTER TABLE.*ADD COLUMN\|ALTER TABLE.*DROP COLUMN\|ALTER TABLE.*MODIFY" app/ src/ --include="*.py" --include="*.ts" --include="*.js"

# 3. 补丁函数的调用点
grep -rn "_ensure_schema\|_patch_schema\|schema_compat\|_ensure_column\|ensureSchema\|EnsureSchema" app/ src/ --include="*.py" --include="*.ts" --include="*.js"
```

## Python + SQLAlchemy/Alembic

### 搜索命令

```bash
# information_schema 查询
grep -rn "information_schema" app/ --include="*.py"

# 启动时的 ALTER TABLE 操作
grep -rn "ALTER TABLE.*ADD COLUMN\|ALTER TABLE.*DROP COLUMN" app/ --include="*.py"

# 补丁函数的调用点
grep -rn "_ensure_schema\|_patch_schema\|schema_compat\|_ensure_column" app/ --include="*.py"
```

### 常见补丁形态

#### 形态 A：硬编码列清单 + 逐列检查

```python
async def _ensure_schema_compatibility():
    patches = {
        "users": [
            ("avatar", "ALTER TABLE users ADD COLUMN avatar VARCHAR(255)"),
        ]
    }
    for table, cols in patches.items():
        for col_name, sql in cols:
            exists = await conn.execute(
                text("SELECT COUNT(*) FROM information_schema.columns WHERE ...")
            )
            if not exists:
                await conn.execute(text(sql))
```

**特征**：函数内有 `information_schema.columns` 查询，外有 `ALTER TABLE` 字符串拼接。

#### 形态 B：启动时无条件 ALTER（try/except 兜底）

```python
async def _patch_schema():
    try:
        await conn.execute(text("ALTER TABLE x ADD COLUMN y INT"))
    except:
        pass  # 列已存在则忽略
```

**特征**：ALTER TABLE 外包裹 try/except:pass，依赖数据库报错来保证幂等。

#### 形态 C：ORM 反射 + 动态 DDL

```python
async def _auto_migrate():
    inspector = inspect(engine)
    for table in Base.metadata.tables.values():
        db_cols = {c["name"] for c in await conn.run_sync(inspector.get_columns, table.name)}
        for col in table.columns:
            if col.name not in db_cols:
                await conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN ..."))
```

**特征**：使用 SQLAlchemy `inspect` / `Inspector`，遍历 `Base.metadata.tables`。

---

## Node.js + Prisma

### 搜索命令

```bash
# Prisma $executeRaw 调用
grep -rn "\$executeRaw\|\$queryRaw" app/ src/ --include="*.ts" --include="*.js"

# ALTER TABLE 操作
grep -rn "ALTER TABLE" app/ src/ --include="*.ts" --include="*.js"

# db push 调用
grep -rn "db push\|prisma.*push" package.json docker-compose* --include="*.yml" --include="*.json"
```

### 常见补丁形态

```typescript
async function ensureSchema() {
  await prisma.$executeRaw`
    ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar VARCHAR(255)
  `
}
```

**特征**：使用 `$executeRaw` 执行 ALTER TABLE，通常在 startup 脚本中调用。

---

## Node.js + TypeORM

### 搜索命令

```bash
# queryRunner 调用
grep -rn "queryRunner\|QueryRunner" app/ src/ --include="*.ts"

# changeColumn / addColumn
grep -rn "changeColumn\|addColumn\|dropColumn" app/ src/ --include="*.ts"
```

### 常见补丁形态

```typescript
async function ensureSchema(queryRunner: QueryRunner) {
  const table = await queryRunner.getTable('users')
  const column = table.findColumnByName('avatar')
  if (!column) {
    await queryRunner.query('ALTER TABLE users ADD COLUMN avatar VARCHAR(255)')
  }
}
```

**特征**：使用 `queryRunner` 执行 DDL，通常在 `createConnection` 后调用。

---

## Django

### 搜索命令

```bash
# RunPython 操作
grep -rn "RunPython\|run_python" app/ --include="*.py"

# state.ops 操作
grep -rn "state.ops\|AddField\|RemoveField\|AlterField" app/ --include="*.py"

# 直接 SQL 执行
grep -rn "cursor.execute\|connection.cursor" app/ --include="*.py" | grep -i "alter\|add column"
```

### 常见补丁形态

```python
def ensure_schema(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE users ADD COLUMN avatar VARCHAR(255)
        """)
```

**特征**：在 migration 的 `RunPython` 操作中直接执行 SQL。

---

## 定位调用入口

```bash
# 补丁函数的调用者
grep -rn "_ensure_schema\|_patch_schema\|ensureSchema\|EnsureSchema" --include="*.py" --include="*.ts" | grep -v "def \|function "

# 常见入口
grep -rn "init_db\|init_mysql\|lifespan\|startup\|on_event\|main\|app.listen\|bootstrap" --include="*.py" --include="*.ts" --include="*.js"
```

### 典型调用链（Python + FastAPI）

```
init_db()              ← 补丁在这里
  ├── create_async_engine()
  ├── _ensure_schema_compatibility()   ← 每次启动执行
  └── return

caller (main.py / celery worker)
  └── create_all()    ← ORM 建表（通常在补丁之后）
```

### 典型调用链（Node.js + Express）

```
bootstrap()            ← 补丁在这里
  ├── PrismaClient()
  ├── ensureSchema()   ← 每次启动执行
  └── app.listen()

caller (index.ts / worker.ts)
  └── prisma db push   ← ORM 建表（通常在补丁之后）
```