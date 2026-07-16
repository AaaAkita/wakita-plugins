# 检查模式参考

本文件提供每个检查项的搜索模式、工具和常见反模式，供 wakita-scout 执行检查时参考。
不放入 SKILL.md 以保持 skill 本身技术栈无关。

---

## 一、安全合规

### 1.1 密钥管理

**搜索模式**:
```bash
# 配置文件中的硬编码密钥
grep -rn "secret\|password\|api_key\|token.*=" \
    docker-compose* .env* config.* settings.* app.config* \
    --include="*.yml" --include="*.yaml" --include="*.py" --include="*.env" --include="*.json"

# git 历史中的密钥
git log -p | grep -i "secret\|password\|api_key" | head -20
```

**常见反模式**:
- docker-compose.yml 中 `JWT_SECRET=test-secret`
- k8s ConfigMap 中明文存储数据库密码
- `.env` 文件被提交到 git
- CI/CD 日志中打印密钥

### 1.2 密钥强度

**搜索模式**:
```bash
grep -rn "SECRET\|secret_key\|encryption_key\|JWT_KEY" \
    .env* config.* --include="*.env" --include="*.py" --include="*.yml"
```

**常见反模式**:
- `JWT_SECRET=your-secret-key`
- `ENCRYPTION_KEY=test-encryption-key-for-development-only`
- `SECRET_KEY=`（空字符串）
- `SECRET=123456`

**修复**: `openssl rand -hex 32`

### 1.3 CORS 配置

**搜索模式**:
```bash
grep -rn "allow_origins\|CORSMiddleware\|cors" \
    --include="*.py" --include="*.js" --include="*.ts"
```

**常见反模式**:
- `allow_origins=["*"]` + `allow_credentials=True`（CSRF 风险）
- 仅在注释中说明"生产环境要改"但无环境变量覆盖

### 1.4 传输加密

**搜索模式**:
```bash
grep -rn "ssl\|listen 443\|Strict-Transport\|https" \
    nginx.conf Caddyfile traefik.toml
```

**常见反模式**:
- nginx 只监听 80 端口，无 443 server block
- 无 HSTS header
- 证书手动管理无自动续期

### 1.5 认证覆盖

**搜索模式**:
```bash
# FastAPI
grep -rn "@router\.\(get\|post\|put\|delete\|patch\)" --include="*.py" | \
    grep -v "Depends\|get_current_user\|require_auth"

# Express
grep -rn "app\.\(get\|post\|put\|delete\)" --include="*.js" | \
    grep -v "auth\|middleware"
```

**常见反模式**:
- 内网 API 认为"不会有人访问"而不加认证
- WebSocket 端点无 token 验证
- 健康检查以外的所有端点都需要认证

### 1.6 权限分级

**搜索模式**:
```bash
grep -rn "role\|admin\|superuser\|is_admin\|require_admin\|permission" \
    --include="*.py" --include="*.ts" --include="*.js"
```

**常见反模式**:
- `is_admin` 字段存在但仅用于用户管理页面
- 敏感词/系统配置/数据导出等操作所有登录用户可执行
- 前端隐藏按钮但后端无权限校验

### 1.7 网络隔离

**搜索模式**:
```bash
grep -A2 "ports:" docker-compose*.yml | grep -E "[0-9]+:[0-9]+"
```

**常见反模式**:
- `6212:3306`（MySQL 暴露到宿主机公网）
- `6380:6379`（Redis 暴露到宿主机公网）
- K8s Service type: LoadBalancer 直接暴露数据库

---

## 二、并发与锁

### 2.1 分布式锁

**搜索模式**:
```bash
grep -rn "SET.*NX\|acquire.*lock\|Lock\|mutex\|redis.*lock" --include="*.py" --include="*.js"
```

**检查要点**:
- 锁获取是否原子（SET NX / 数据库 INSERT UNIQUE）
- 释放是否校验持锁者身份（Lua 脚本 / compare-and-delete）
- TTL 是否大于任务最大执行时间 + buffer
- 是否有锁续期（watchdog/renew）

### 2.2 请求限流

**搜索模式**:
```bash
grep -rn "rate.limit\|limiter\|throttle\|slowapi\|express-rate-limit" \
    --include="*.py" --include="*.js" --include="*.ts"
```

**常见反模式**:
- 全项目无任何限流
- 仅限流登录但爬虫/注册/AI 生成等昂贵端点不限流
- 限流基于内存（多实例不同步）

### 2.3 任务去重

**搜索模式**:
```bash
grep -rn "cron\|schedule\|periodic\|beat\|celery.*task" \
    --include="*.py" --include="*.js" --include="*.yml"
```

**常见反模式**:
- Beat 触发后直接执行，不检查上次是否完成
- 多 Worker 同时消费同一任务
- 任务幂等性依赖"感觉不会并发"

### 2.4 全局状态

**搜索模式**:
```bash
grep -rn "^_[a-z].*:.*[Dd]ict\|^_[a-z].*:.*[Ss]et\|^_[a-z].*=.*{}" --include="*.py"
grep -rn "global_state\|module.*level.*cache\|singleton" --include="*.py"
```

**常见反模式**:
- WebSocket 连接集 `_active: Set[WebSocket]` 只增不删
- 浏览器实例缓存无 TTL
- 登录会话字典无定期过期清理

---

## 三、数据完整性

### 3.1 数据备份

**搜索模式**:
```bash
find . -name "backup*" -o -name "dump*" -o -name "snapshot*" | head -20
grep -rn "mysqldump\|pg_dump\|mongodump\|BGSAVE\|snapshot" scripts/ --include="*.sh"
```

**检查要点**:
- 覆盖所有持久化存储（MySQL + Redis + 向量DB + 对象存储）
- 备份周期（日级）+ 保留策略（≥7天）
- 异地/远程同步
- 恢复脚本 + 最近一次恢复演练记录

### 3.2 失败重试

**搜索模式**:
```bash
grep -rn "autoretry\|max_retries\|retry\|self.retry\|task_retry" \
    --include="*.py" --include="*.js"
```

**常见反模式**:
- Celery 任务只配了全局 `max_retries=3` 但无 `self.retry()` 调用
- 所有异常都重试（包括数据验证错误）
- 重试无退避（固定间隔）

### 3.3 输入容错

**搜索模式**:
```bash
grep -rn "except.*:.*pass\|except.*:.*continue" --include="*.py" | \
    grep -i "json\|parse\|decode\|csv\|xml"
```

**常见反模式**:
- `except json.JSONDecodeError: pass` 不记日志
- 流式数据中坏行静默跳过
- 无 dead letter 机制

### 3.4 写入冲突

**搜索模式**:
```bash
grep -rn "upsert\|insert.*update\|ON CONFLICT\|ON DUPLICATE\|SELECT.*FOR UPDATE\|optimistic\|version" \
    --include="*.py" --include="*.js"
```

**常见反模式**:
- upsert 直接 UPDATE 覆盖
- 多实例同时写同一记录无版本检查
- 用户配置/状态等高频更新无冲突处理

### 3.5 连接池

**搜索模式**:
```bash
grep -rn "pool_size\|max_overflow\|max_connections\|connectionLimit\|pool:" \
    --include="*.py" --include="*.js" --include="*.yml"
```

**常见反模式**:
- 连接池无上限
- session/connection 手动 open/close（忘记 close 导致泄漏）
- pool_recycle 长于数据库 wait_timeout

---

## 四、可观测性

### 4.1 健康检查

**搜索模式**:
```bash
grep -rn "health\|/health\|healthz\|readiness\|liveness" \
    --include="*.py" --include="*.js" --include="*.yml"
```

**常见反模式**:
- `return {"status": "ok"}` 不做实际检查
- 检查 DB 但不检查 Cache/Queue
- 无超时（卡死阻塞）

### 4.2 指标暴露

**搜索模式**:
```bash
grep -rn "prometheus\|metrics\|/metrics\|statsd\|opentelemetry" \
    --include="*.py" --include="*.js" --include="*.yml"
```

**检查要点**:
- 请求计数 + 延迟分布
- 后台任务成功/失败/耗时
- 业务指标（如爬取量/用户数）

### 4.3 告警通知

**搜索模式**:
```bash
grep -rn "webhook\|dingtalk\|wecom\|slack\|smtp\|notification\|alert" \
    --include="*.py" --include="*.js"
```

**常见反模式**:
- `send_notifications` 是空函数/stub
- 仅有日志无外部通知
- 所有级别事件都发通知（告警疲劳）

### 4.4 日志规范

**检查要点**:
- 是否 JSON 格式
- 是否含 timestamp/level/service/trace_id
- 是否有请求 ID 贯穿调用链
- 日志级别是否合理（DEBUG/INFO/WARNING/ERROR）

---

## 五、外部依赖与网络

### 5.1 外部调用

**搜索模式**:
```bash
grep -rn "httpx\|aiohttp\|requests\.\|axios\|fetch\|got(" --include="*.py" --include="*.ts" | \
    grep -v "timeout"
```

**常见反模式**:
- 外部 HTTP 调用无 timeout
- 依赖外部服务但无降级方案

### 5.2 频率控制

**搜索模式**:
```bash
grep -rn "sleep\|time\.sleep\|asyncio\.sleep\|setTimeout\|setInterval" --include="*.py" --include="*.ts" | \
    grep -v "random\|uniform\|jitter"
```

**常见反模式**:
- 固定 `sleep(2)` 延迟
- 所有平台/接口使用相同间隔

### 5.3 解析容错

同 3.3，额外检查：
- 外部 API 响应格式变更是否导致崩溃
- 字符编码问题（GBK/UTF-8 混用）

### 5.4 长连接管理

**搜索模式**:
```bash
grep -rn "WebSocket\|SSE\|EventSource\|ping\|pong\|heartbeat" \
    --include="*.py" --include="*.ts" --include="*.js"
```

**常见反模式**:
- WebSocket 无 token 认证
- 无心跳超时断开
- 前端无断线重连

---

## 六、部署与运维

### 6.1 资源限制

**搜索模式**:
```bash
grep -rn "resources:\|limits:\|cpus:\|memory:\|mem_limit\|cpuset" \
    docker-compose* --include="*.yml" --include="*.yaml"
```

**常见反模式**:
- compose 中全服务无 `deploy.resources.limits`
- K8s 中无 resource requests/limits

### 6.2 容器健康

**搜索模式**:
```bash
grep -rn "healthcheck\|HEALTHCHECK\|livenessProbe\|readinessProbe" \
    Dockerfile* docker-compose* k8s/
```

### 6.3 优雅关机

**搜索模式**:
```bash
grep -rn "shutdown\|lifespan\|graceful\|SIGTERM\|SIGINT\|beforeunload\|cleanup\|close\|dispose" \
    --include="*.py" --include="*.js" | grep -v test | grep -v node_modules
```

**常见反模式**:
- `cleanup()` 方法存在但无任何地方调用
- 收到 SIGTERM 后立即退出不等请求完成
- 子进程/Chrome 实例退出后未回收

### 6.4 单点风险

**检查要点**:
- 数据库单实例 → 有备份方案
- 缓存单实例 → 有持久化（AOF/RDB）
- 消息队列单实例 → 任务持久化 + 重试
- 无自动故障转移 → 文档化 MTTR 预期