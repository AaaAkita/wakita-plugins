# Docker 项目部署通用模板 (Reference)

此文档作为项目容器化的标准模板。请根据实际技术栈（{{STACK}}）替换相应部分。

---

## 一、Dockerfile 核心模板

### 1.1 依赖与生产分离（最佳实践）

```dockerfile
# 选择基础镜像: node:{{VERSION}}-alpine / python:{{VERSION}}-slim
FROM {{BASE_IMAGE}} AS builder

WORKDIR /app

# ✅ 仅复制依赖清单以利用缓存
COPY {{DEP_FILE_1}} {{DEP_FILE_2}} ./
{{INSTALL_COMMAND}}

# 复制源码并构建
COPY . .
{{BUILD_COMMAND}}

# --- 运行阶段 ---
FROM {{RUN_IMAGE}}
{{RUN_SETUP}}
COPY --from=builder /app/{{BUILD_OUTPUT}} {{RUN_DEST}}

EXPOSE {{INTERNAL_PORT}}
{{START_COMMAND}}
```

### 1.2 前端 Vite 项目 Dockerfile（实战模板）

此模板针对 Vue/React + Vite + Nginx 的前端项目，综合了安全加固与性能优化。

```dockerfile
# ============================================================
# Build stage
# ============================================================
FROM m.daocloud.io/docker.io/node:20-alpine AS builder

WORKDIR /app

# Configure registry mirrors for China
ENV npm_config_registry=https://registry.npmmirror.com

# Use domestic mirror for Alpine packages
RUN sed -i 's|dl-cdn.alpinelinux.org|mirrors.aliyun.com|g' /etc/apk/repositories

# Copy dependency files first for better layer caching
COPY package*.json ./
RUN npm ci

# Copy source code (test files excluded by .dockerignore)
COPY . .

# Build production bundle
RUN npm run build

# ============================================================
# Production stage
# ============================================================
FROM m.daocloud.io/docker.io/nginx:alpine

# Create non-root user for nginx
RUN adduser -D -H -s /sbin/nologin nginxuser && \
    chown -R nginxuser:nginxuser /var/cache/nginx /var/log/nginx /usr/share/nginx/html

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config to avoid conflicts
RUN rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

# Switch to non-root user
USER nginxuser

CMD ["nginx", "-g", "daemon off;"]
```

**关键实践说明：**

| 实践 | 原因 |
|------|------|
| `node:20-alpine` | Node 18 已于 2025 停止维护，20 是当前 LTS |
| `npm ci` | 严格根据 lockfile 安装，保证构建可复现 |
| `package*.json` 先复制 | 利用 Docker 分层缓存，依赖不变时无需重新 npm ci |
| 非 root 运行 `nginxuser` | 容器安全最佳实践，降低攻击面 |
| `HEALTHCHECK` | Docker 自动检测容器健康，异常时自动重启 |
| `rm -f /etc/nginx/conf.d/default.conf` | 避免默认配置与自定义配置冲突 |

**常见反模式与注意：**
- 如果项目同时有 `package-lock.json` 和 `pnpm-lock.yaml`，**优先使用 npm**（`pnpm install --frozen-lockfile` 在 lockfile 与 package.json 不同步时会直接失败）。
- 不要试图在 Dockerfile 里修复 `frozen-lockfile` 同步问题——应在本地运行 `npm install` 或 `pnpm install` 更新 lockfile 后再构建。

### 1.3 后端 Python 项目 Dockerfile（含缓存挂载实战模板）

此模板针对 Python 后端项目，演示如何用 cache mount 把构建从分钟级降到秒级。

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 时区
ENV TZ=Asia/Shanghai

# 国内镜像源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/*.sources 2>/dev/null || true

# ✅ 系统依赖层 —— 配 cache mount，apt 包不再重复下载
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    {{APT_PKGS}} \
    && rm -rf /var/lib/apt/lists/*

# ✅ 依赖清单先 COPY（改代码时不击穿这一层）
COPY requirements.txt .
# ✅ pip 层 —— 配 cache mount，wheel 包不再重复下载
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 代码层最后
COPY . .

# 非 root 运行
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "main.py"]
```

---

## 二、构建缓存配置（关键提速章节）

### 2.1 双层缓存机制

Docker 构建有**两层缓存**，必须都理解：

#### 第 1 层：BuildKit 层缓存（→ `CACHED`）

每行 `RUN`/`COPY` 是一层，指令不变则命中 `CACHED`，零耗时零下载。改 `COPY . .`（代码）只击穿该层及之后，依赖层不受影响。

#### 第 2 层：BuildKit 缓存挂载（→ 层失效也兜底）

`--mount=type=cache` 把下载内容持久化到宿主机。即使对应 RUN 层失效重跑，下载内容仍从本地缓存读，不联网。这是"提升官方依赖共用率"的核心机制。

### 2.2 cache mount 模板（各语言通用）

```dockerfile
# apt（Debian/Ubuntu 系）
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends <pkgs>

# pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# npm
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# apk（Alpine）
RUN --mount=type=cache,target=/var/cache/apk \
    apk add --no-cache <pkgs>
```

`sharing=locked`：多并发构建共用同一 cache mount 时串行访问，避免损坏（单线程构建可不加）。

### 2.3 跨项目共用缓存（提升"官方依赖共用率"）

默认每个项目的 cache mount **按工作目录隔离**，互不共用。要让多个项目复用同一份官方依赖缓存，给**相同的 `id`**：

```dockerfile
# 项目 A、B 的 Dockerfile 都用同一 id
RUN --mount=type=cache,id=shared-pip,target=/root/.cache/pip \
    pip install -r requirements.txt
```

| 共用范围 | 默认 | 提升方式 |
|---------|------|---------|
| 同项目多次构建 | ✅ 自动 | 无需配置 |
| 跨项目共用 | ❌ 隔离 | 相同 `id`，或 `--cache-to/--cache-from type=local` |

注意：pip/apt 按"包名+版本"去重，跨项目冲突极小；但 **Python 版本不同则 wheel 不通用**，需按版本分 id（如 `id=shared-pip-py311`）。

### 2.4 缓存存到哪了

- **Linux**：`/var/lib/docker/buildkit/` 下
- **Docker Desktop（Windows/Mac）**：在 Docker Desktop 虚拟磁盘（WSL2 的 ext4 虚拟盘）内部，不直接暴露给宿主文件系统
- 查看：`docker buildx du`；清理：`docker buildx prune --filter type=exec.cachemount`

### 2.5 判断缓存命中（必须 `--progress plain`）

```bash
docker compose build <service> --progress plain
```

| 日志 | 含义 |
|------|------|
| `CACHED` | 层缓存命中，零耗时 |
| 秒级完成无下载 | cache mount 兜底生效 |
| 大量下载 + 分钟耗时 | 未命中，需排查 |

### 2.6 击穿缓存的改动

| 改动 | 影响范围 | cache mount 兜底 |
|------|---------|-----------------|
| 应用代码（`COPY . .`） | 仅该层及之后 | 不涉及下载 |
| 任意 `RUN` 指令变动 | 该层及之后重跑 | ✅ |
| `requirements.txt`/`package.json` | 依赖层重跑 | ✅ 只下新增包 |
| 切换 `FROM` | 几乎全重跑 | ✅ |

### 2.7 `.dockerignore` 血案（必读）

曾因缺失 `.dockerignore`，本地 `venv`(947MB)、`browser_data`(77MB)、docs(20MB) 全被 `COPY . .` 拷进构建上下文，`chown -R` 改这 1GB+ 文件属主，**单步卡死 13 分钟**。

**排障信号**：构建长时间卡在 `COPY . .` 或 `RUN chown -R` → 第一反应查 `.dockerignore`。

---

## 三、国内镜像加速配置

### 3.1 包管理器镜像源

| 工具 | 配置文件/命令 | 推荐镜像源 |
|------|--------------|-----------|
| **npm** | `.npmrc` | `registry=https://registry.npmmirror.com` |
| **pip** | `pip install` | `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| **apt** | `sources.list` | `mirrors.aliyun.com` |
| **apk** | `/etc/apk/repositories` | `mirrors.aliyun.com` |

### 3.2 Docker Hub 镜像加速

```dockerfile
# 镜像源前缀加速拉取
FROM m.daocloud.io/docker.io/node:20-alpine
```

或配置 Docker Desktop `registry-mirrors`。

---

## 四、通用 Nginx 反代模板 ({{APP_NAME}})

### 4.1 标准 SPA + API 代理模板

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;

    # 接口转发
    location {{API_PREFIX}} {
        proxy_pass         http://{{BACKEND_SERVICE}}:{{BACKEND_PORT}};
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;

        # 长连接/大文件配置
        proxy_read_timeout {{TIMEOUT}};
        proxy_buffering    off;
    }

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    client_max_body_size {{MAX_UPLOAD_SIZE}};
}
```

### 4.2 生产级 Vite SPA 模板（含性能与安全优化）

此模板适用于 Vite 构建的前端项目，带有 hash 的资源文件在 `dist/assets/` 目录下。

```nginx
server {
    listen       80;
    server_name  localhost;
    client_max_body_size 50M;

    # Gzip 压缩 —— 减少静态资源传输体积
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # 安全响应头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 静态资源（Vite 构建后的 hash 文件）—— 长期缓存 + 关闭日志
    location /{{BASE_PATH}}/assets/ {
        alias   /usr/share/nginx/html/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # SPA 路由 —— 不缓存 index.html，避免路由缓存导致更新不生效
    location /{{BASE_PATH}}/ {
        alias   /usr/share/nginx/html/;
        try_files $uri $uri/ /{{BASE_PATH}}/index.html;
        add_header Cache-Control "no-cache";
    }

    # 根路径重定向
    location = / {
        absolute_redirect off;
        return 301 /{{BASE_PATH}}/;
    }

    # 后端 API 代理（带 base path）
    location /{{BASE_PATH}}/api/ {
        proxy_pass http://{{BACKEND_SERVICE}}:{{BACKEND_PORT}}/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket 代理
    location /{{BASE_PATH}}/api/v1/ws/ {
        proxy_pass http://{{BACKEND_SERVICE}}:{{BACKEND_PORT}}/api/v1/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

**缓存策略设计逻辑：**

| 资源类型 | 缓存策略 | 原因 |
|----------|----------|------|
| `assets/*` (hash 文件) | `immutable` + 1 年 | Vite 构建后文件名含 hash，内容永不变 |
| `index.html` | `no-cache` | SPA 入口文件，每次请求需确认是否有更新 |
| API 请求 | 无缓存 | 动态数据，不可缓存 |

---

## 五、Docker Compose 编排模板

```yaml
services:
  {{SERVICE_NAME}}:
    build:
      context: {{BUILD_CONTEXT}}
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: .env
    ports:
      - "{{EXT_PORT}}:{{INT_PORT}}"
    volumes:
      - {{DATA_VOLUME}}:/app/data
    healthcheck:
      test: ["CMD", "{{HEALTH_CHECK_CMD}}"]
      interval: 30s
```

### 5.1 开发环境（Bind Mount 热重载）

```yaml
services:
  {{SERVICE_NAME}}:
    image: {{BASE_IMAGE}}          # 直接用官方镜像，不 build
    volumes:
      - ./{{SRC_DIR}}:/app         # 挂载源码，改代码立即生效
      - {{DATA_VOLUME}}:/app/data
    command: {{DEV_COMMAND}}       # 热重载命令
```

### 5.2 生产环境（Named Volume 严格持久化）

```yaml
services:
  {{SERVICE_NAME}}:
    build:
      context: {{BUILD_CONTEXT}}
    restart: unless-stopped
    volumes:
      - {{NAMED_VOLUME}}:/app/data  # Named Volume，独立于容器
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
```

---

## 六、.dockerignore 必选列表

```gitignore
# 依赖目录（镜像内自己装）
node_modules/
venv/
.venv/

# 构建产物
dist/
build/

# 敏感配置与密钥
.env
.env.*
.git/

# 日志与缓存
*.log
__pycache__/
*.pyc

# 运行时数据（应走卷，不进镜像）
logs/
htmlcov/
browser_data/

{{CUSTOM_EXCLUDES}}
```

**判断标准**：凡是"镜像内会自己重新生成"或"运行时通过卷挂载"的东西，都应排除。拿不准时，宁可多排，因为进上下文的每 MB 都会被 `chown -R` 之类的指令放大成多倍耗时。
