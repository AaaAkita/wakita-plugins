# 基线检查模式参考

本文件提供每个检查项的搜索模式、工具和常见反模式，供 wakita-scout 执行检查时参考。
保持技术栈无关，检查方法适用于所有语言和框架。

---

## 一、安全底线

### 1. 密钥不入库

**搜索模式**:
```bash
# 配置文件中的硬编码密钥
grep -rn "secret\|password\|api_key\|token.*=\|PRIVATE_KEY" \
    --include="*.yml" --include="*.yaml" --include="*.py" --include="*.env" \
    --include="*.json" --include="*.js" --include="*.ts" --include="*.toml" \
    docker-compose* config* settings* app.config* .env* 2>/dev/null

# .env 是否被 gitignore
grep -F ".env" .gitignore 2>/dev/null

# git 历史中是否泄露过密钥
git log -p --all | grep -i "secret\|password\|api_key\|private_key" | head -20
```

**常见反模式**:
- `docker-compose.yml` 中 `JWT_SECRET=my-secret-key`
- `config.py` 中 `DATABASE_PASSWORD = "admin123"`
- `.env` 被提交到 git 仓库
- CI/CD 日志中打印了密钥
- 注释掉的旧密钥仍留在代码中

**修复**:
- 所有密钥收入 `.env`，提供 `.env.example` 模板（仅列变量名，不写值）
- 确保 `.env` 在 `.gitignore` 中
- 清理 git 历史：`git filter-branch` 或 `BFG Repo-Cleaner`

---

### 2. 入口输入校验

**搜索模式**:
```bash
# Python FastAPI: 路由定义中无类型注解或校验
grep -rn "@router\.\(post\|put\|patch\)" --include="*.py" | while read line; do
    echo "$line"
    # 检查该路由函数参数是否有 Pydantic schema
done

# Python: 直接取 request body 而不校验
grep -rn "request\.json()\|request\.body\|request\.data\|request\.form" --include="*.py"

# JavaScript/TypeScript: 路由中无校验中间件
grep -rn "router\.\(post\|put\|patch\)" --include="*.ts" --include="*.js" | \
    grep -v "validate\|schema\|zod\|joi\|yup"

# 通用: 裸用用户输入拼 SQL / 命令 / 路径
grep -rn "exec(\|os\.system\|subprocess\|eval(" --include="*.py" --include="*.js"
```

**常见反模式**:
- `def login(request): data = request.json()` 直接取值不校验字段存在
- SQL 拼接：`f"SELECT * FROM users WHERE id = {user_id}"`
- 文件路径拼接：`open(f"/data/{filename}")` — 路径穿越
- 邮箱/手机号格式无正则校验

**修复**: 
- Python: Pydantic / Marshmallow
- JS/TS: Zod / Joi / Yup
- 通用: 参数化查询（防注入）、路径白名单校验

---

### 3. 鉴权覆盖

**搜索模式**:
```bash
# 查找路由定义，排除已有认证依赖的
# Python FastAPI
grep -rn "@router\.\(get\|post\|put\|delete\|patch\)" --include="*.py" | \
    grep -v "Depends\|get_current_user\|require_auth\|auth_required"

# Express/Koa
grep -rn "router\.\(get\|post\|put\|delete\)\|app\.\(get\|post\|put\|delete\)" \
    --include="*.ts" --include="*.js" | \
    grep -v "auth\|middleware\|isAuth\|requireAuth"

# 检查公开端点是否有注释说明
grep -rn "@router\.\(get\|post\)" --include="*.py" | \
    grep -i "login\|register\|health"
```

**常见反模式**:
- 内网 API 无认证（"反正外面访问不到"）
- WebSocket 连接无 token 验证
- 仅前端隐藏按钮、后端无权限检查
- `/api/admin/*` 路由无独立鉴权

**修复**: 全局注册认证中间件，公共端点显式声明跳过认证（带注释）

---

## 二、数据底线

### 4. Schema as Code

**搜索模式**:
```bash
# 确认有 migration 目录或工具配置
find . -type d -name "migrations" 2>/dev/null
find . -name "alembic.ini" -o -name "knexfile.*" -o -name "prisma" 2>/dev/null

# 裸建表语句（反模式信号）
grep -rn "CREATE TABLE\|ALTER TABLE\|CREATE INDEX\|DROP TABLE" \
    --include="*.py" --include="*.js" --include="*.ts" --include="*.sql" | \
    grep -v "migration\|alembic"

# ORM 的 create_all / sync 调用（启动时自动建表，但无迁移记录）
grep -rn "create_all\|metadata.create_all\|sync({.*force" --include="*.py" --include="*.ts"
```

**常见反模式**:
- `Base.metadata.create_all(bind=engine)` 在启动时自动建表 — 无版本历史
- 生产环境手动执行过 `ALTER TABLE` 但 migration 文件中没有
- migration 目录存在但内容为空
- 仅开发库跑过 migration，生产库表结构是手动建的

**修复**: 
- Python: Alembic（`alembic init migrations` → `alembic revision --autogenerate`）
- JS/TS: Knex Migrations / Prisma Migrate / TypeORM Migrations
- 禁止启动时自动建表，改为 `alembic upgrade head`

---

### 5. 环境隔离

**搜索模式**:
```bash
# 查找环境配置文件
find . -name ".env*" -not -name ".env.example" 2>/dev/null
find . -name "config*" -name "settings*" 2>/dev/null | head -10

# 检查是否有 dev/prod 分离
grep -l "environ\|ENV\|PRODUCTION\|DEV" config* settings* .env* 2>/dev/null

# 检查 docker-compose 是否区分环境
ls docker-compose*.yml 2>/dev/null

# 硬编码的连接字符串（跨环境共用风险）
grep -rn "DATABASE_URL\|MONGO_URI\|REDIS_URL\|MYSQL_HOST" \
    --include="*.py" --include="*.env" --include="*.yml" | \
    grep -v "os\.getenv\|process\.env\|environ"
```

**常见反模式**:
- 只有一个 `.env` 文件，所有环境共用
- 开发环境直连生产数据库
- `config.py` 中 `if DEBUG: ... else: ...` 但 `DEBUG` 永远为 `True`
- docker-compose 中 hardcode `ENV=development`

**修复**:
- `.env.dev` / `.env.prod` 分离，启动时指定
- 或用 `NODE_ENV` / `APP_ENV` 环境变量切换配置源
- 数据库连接串永远走环境变量

---

## 三、架构底线

### 6. 前后端分离

**搜索模式**:
```bash
# 检查目录结构
ls -d frontend* backend* client* server* web* api* 2>/dev/null

# 后端渲染模板（反模式信号）
grep -rn "render_template\|res\.render\|ejs\.render\|pug\|handlebars\|jinja" \
    --include="*.py" --include="*.js" --include="*.ts" | \
    grep -v "test"

# 前端代码中直接引用后端模块
grep -rn "from backend\|from api\|from server\|require.*\.\.\/backend" \
    --include="*.js" --include="*.ts" --include="*.py"

# 确认前端通过 API 通信
grep -rn "fetch\|axios\|http\.\|requests\." frontend/ --include="*.ts" --include="*.js" 2>/dev/null | head -5
```

**常见反模式**:
- `app.py` 里同时挂 API 路由和渲染 HTML
- 前端源码放在 `backend/static/` 下由后端 serve
- 前端 `import` 了后端的类型定义文件（源码级耦合）

**修复**: 前后端分目录，前端独立 dev server，仅通过 API 通信

---

### 7. 统一响应信封

**搜索模式**:
```bash
# 查找 API 返回格式
grep -rn "return.*json\|res\.json\|JSONResponse\|return \[" \
    --include="*.py" --include="*.ts" --include="*.js" | \
    grep -v "success\|code\|message\|data"

# 查找是否有统一响应工具函数
grep -rn "def success\|def error\|class.*Response\|response.*success\|sendSuccess\|sendError" \
    --include="*.py" --include="*.ts" --include="*.js"

# 版本前缀
grep -rn "api/v[0-9]\|APIRouter.*prefix\|router.*prefix.*api" \
    --include="*.py" --include="*.ts" --include="*.js"

# 全局异常处理
grep -rn "exception_handler\|errorHandler\|error_middleware\|@app\.errorhandler" \
    --include="*.py" --include="*.ts" --include="*.js"
```

**常见反模式**:
- 不同接口返回格式不同：有的 `{"data": [...]}`，有的直接 `[...]`
- 成功和失败返回结构不一致
- 路由无版本前缀：`/api/user` 而非 `/api/v1/user`
- 500 错误直接暴 Flask/Django traceback 给前端

**修复**: 
- 定义统一响应函数 `success(data)`, `error(msg, code)`
- 全局异常处理 → `{ success: false, code: 500, message: "内部错误", data: null }`
- 所有路由注册在 `/api/v1` 前缀下

---

### 8. 异常不静默

**搜索模式**:
```bash
# 空 catch 块
grep -rn "except.*:" --include="*.py" -A2 | grep -B2 "pass\|\.\.\.$"
grep -rn "catch" --include="*.ts" --include="*.js" -A2 | grep -B2 "{}"

# 吞错型 except（捕获所有异常但不处理）
grep -rn "except:\|except Exception:" --include="*.py" | \
    grep -v "log\|logger\|logging\|print\|traceback"

# 静默转换错误为成功
grep -rn "except.*:\|\.catch" --include="*.py" --include="*.ts" | \
    grep -v "raise\|throw\|logger\|log\|print"
```

**常见反模式**:
```python
# Python 典型吞错
try:
    result = external_api.call()
except Exception:
    pass  # 💀 出错了也不知道

# 或更隐蔽
except Exception:
    return {"success": True, "data": []}  # 💀 把错误当空结果返回
```

**修复**:
- 全局异常处理器兜底
- 业务 catch 块最少 `logger.exception("xxx失败")`
- 不可恢复的错误 re-raise

---

## 四、工程底线

### 9. 依赖可复现

**搜索模式**:
```bash
# 确认有锁定文件
ls requirements.txt poetry.lock Pipfile.lock package-lock.json yarn.lock pnpm-lock.yaml \
    Cargo.lock go.sum Gemfile.lock 2>/dev/null

# 检查是否用了浮动版本
grep -E "==|@|~|\^" requirements.txt package.json 2>/dev/null
grep -E "latest|\*" package.json 2>/dev/null
```

**常见反模式**:
- `requirements.txt` 中 `flask` 不写版本号
- `package.json` 中大量 `"*"` 或 `"latest"`
- 有 `package-lock.json` 但被 `.gitignore` 排除
- Poetry 项目只提交 `pyproject.toml` 不提交 `poetry.lock`

**修复**: 
- Python: 用 `pip freeze > requirements.txt` 或 Poetry lock
- JS/TS: 提交 `package-lock.json` / `yarn.lock`
- 版本全部精确锁定

---

### 10. README 可启动

**判定要点**（不要 grep，直接阅读 README，看是否包含以下信息）:

- [ ] 克隆命令：`git clone <url>`
- [ ] 安装命令：`pip install -r requirements.txt` / `npm install`
- [ ] 环境变量说明：列出所有必填的 `.env` 变量
- [ ] 启动命令：`python app.py` / `npm run dev`
- [ ] 默认端口号：`服务运行在 http://localhost:8000`
- [ ] 数据库初始化（如有）：migration 运行命令

**常见反模式**:
- README 只有项目标题，没有任何启动说明
- 写了安装步骤但漏掉某个系统依赖（如 "需要先装 Redis"）
- 环境变量只写了变量名，没写含义和示例值
- 多服务项目（前端+后端）只写了后端的启动方式

**修复**: 从零开始 clone → install → run 一遍，卡在哪里补哪里
