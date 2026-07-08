---
name: docker-expert
description: 提供 Docker 构建缓存复用、部署规范审查、多环境配置及问题诊断。涵盖 BuildKit 缓存挂载、镜像优化、Compose 编排与生产可靠性最佳实践。
---

# Docker 专家技能 (Docker Expert Skill)

作为 Docker 专家，你负责确保项目的容器化配置**构建快、镜像小、跑得稳、符合最佳实践**。

本 skill 由两部分整合而成：
- **构建缓存复用**（原 `docker-backend-cache-build`）：解决"每次构建都超长时间重新下载"的痛点
- **通用部署规范**（原 AaaAkitaSkills `docker-expert`）：Dockerfile/Compose 标准化、安全加固、多环境指导

---

## 一、何时触发

- 用户说"重新构建""docker build""重构镜像""构建太慢""构建卡住/卡死"
- 用户问"构建缓存存到哪了""怎么复用缓存""挂载代码和构建代码的区别"
- 需要停止构建/构建卡住/引擎崩溃后恢复（见 3.8 构建管理纪律）
- 需要审查/编写 Dockerfile、docker-compose.yml、.dockerignore
- 用户询问开发环境 vs 生产环境的容器化差异
- 镜像构建失败需重试或排查

---

## 二、构建缓存机制（核心：让构建从"分钟级"降到"秒级"）

### 2.1 双层缓存模型

Docker 构建有**两层缓存**，理解清楚才能定位"为什么又重新下载了"。

#### 第 1 层：BuildKit 层缓存（RUN/COPY 层命中 → 显示 `CACHED`）

Dockerfile 每一行 `RUN`/`COPY` 是一层，Docker 记下每层结果。**只要该行指令没变，下次构建直接复用上一次的成果**，日志显示 `CACHED`，零耗时零下载。

- 改了 `COPY . .`（应用代码）→ 只有这一层及之后的层失效
- 装依赖的层（apt/pip/chromium）只要指令不变 → **CACHED，不重新下**

#### 第 2 层：BuildKit 缓存挂载（cache mount → 层失效也兜底，关键提速手段）

通过 `--mount=type=cache` 把"下载的东西"持久化到宿主机独立区域。**即使对应 RUN 层失效重跑，下载内容仍从本地缓存读，不联网。**

这是"提升官方依赖共用率"的核心机制。典型挂载：

| 挂载目标 | 持久化内容 | 典型体积 |
|---------|-----------|---------|
| `/var/cache/apt` + `/var/lib/apt` | apt 的 .deb 包 | 数百 MB |
| `/root/.cache/pip` | pip wheel 包（numpy/torch 等重依赖） | ~1GB |
| `~/.npm` 或 pnpm store | npm/pnpm 包 | 数百 MB |
| 浏览器二进制缓存目录 | chromium/playwright 二进制 | 数百 MB |

### 2.2 "缓存存到哪了"

默认存在 Docker 的内部存储区（BuildKit 管的 cache mount 目录）：

- **Linux**：`/var/lib/docker/buildkit/` 下
- **Docker Desktop（Windows/Mac）**：在 Docker Desktop 虚拟磁盘（WSL2 的 ext4 虚拟盘）内部，不直接暴露给宿主文件系统

每个 cache mount 按"工作目录 + id"隔离。可用 `docker buildx du` 查看缓存占用，`docker buildx prune` 清理。

### 2.3 cache mount 的"共用率"——两个层面要分清

用户常问"缓存挂载能不能提升官方依赖共用率"，答案分两种情况：

| 共用范围 | 默认行为 | 提升方式 |
|---------|---------|---------|
| **同一项目多次构建**（最常见） | ✅ 自动共用 | 不需额外配置，cache mount 天然持久化 |
| **跨项目共用**同一份官方依赖缓存 | ❌ 默认隔离（按工作目录分桶） | 显式给相同的 `id`，或用 `--cache-to/--cache-from` 导出共享 |

#### 跨项目共用写法（给相同 `id`）

```dockerfile
# 项目 A 和项目 B 的 Dockerfile 都用同一个 id
RUN --mount=type=cache,id=shared-pip,target=/root/.cache/pip \
    pip install -r requirements.txt
```

> 注意：pip/apt 是按"包名+版本"去重存储的，不同项目的依赖同名同版本会复用同一份缓存，冲突极小。但若两个项目 Python 版本不同，wheel 不通用，需按版本分 `id`（如 `id=shared-pip-py311`）。

### 2.4 如何判断缓存是否命中

构建时**必须加 `--progress plain`**，否则看不到每层状态：

```bash
docker compose build <service> --progress plain
# 或
docker build --progress plain -t <image> .
```

日志判读：

| 日志特征 | 含义 |
|---------|------|
| `CACHED` | 层缓存命中，零耗时零下载 |
| 某层秒级完成（非 `CACHED`）但无下载 | cache mount 兜底生效，从本地读缓存 |
| 某层出现大量下载 + 分钟级耗时 | 缓存未命中，需排查原因 |

### 2.5 哪些改动会击穿缓存

| 改动 | 影响范围 | cache mount 是否兜底 |
|------|---------|---------------------|
| 应用代码变动（`COPY . .`） | 仅该层及之后 | 不涉及下载，无需兜底 |
| Dockerfile 任意 `RUN` 指令变动 | 该层及之后全部重跑 | ✅ 兜住下载 |
| `requirements.txt`/`package.json` 变动 | 依赖层重跑 | ✅ 只下新增包 |
| 切换基础镜像（`FROM`） | 几乎全部重跑 | ✅ 兜住，但系统级包可能需重下 |

**最大优势**：应用代码变动只击穿最后的 `COPY` 层，依赖层完全不受影响——这是把 Dockerfile 分层写对的核心收益。

---

## 三、加速构建实操清单

### 3.1 改业务代码时——根本别 build

挂载模式下（见第四节），运行时用的是挂载进来的代码，不是镜像里 COPY 的代码。改业务代码只需重启：

```bash
docker compose restart <service>
```

只有**改依赖**（pip 包、apt 包、浏览器二进制）才需要重新 build。

### 3.2 必须构建时——保证缓存自动命中

Dockerfile 里**依赖层必须在代码层之前**：

```dockerfile
COPY requirements.txt .            # 依赖清单先 COPY
RUN pip install -r requirements.txt  # 依赖层在前
COPY . .                           # 代码层在后
```

这样改代码只击穿最后的 `COPY`，依赖层全部 `CACHED`。

### 3.3 cache mount 模板（务必配上）

```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends <pkgs>

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

`sharing=locked` 表示多个并发构建共用同一 cache mount 时串行访问，避免损坏。

### 3.4 构建带 `--progress plain` 看缓存命中

见 2.4。

### 3.5 `.dockerignore` 必须有（最易踩的坑，曾致构建卡死 13 分钟）

**血案**：曾因缺失 `.dockerignore`，本地 `venv`(947MB)、`browser_data`(77MB)、docs(20MB) 全被 `COPY . .` 拷进构建上下文，`chown -R` 递归改这 1GB+ 文件属主，单步卡死 13 分钟。

**必排除的大目录**：

| 排除项 | 原因 |
|--------|------|
| `venv/` / `.venv/` | 本地虚拟环境（镜像内自己装） |
| `node_modules/` | 同上 |
| `dist/` / `build/` | 构建产物 |
| `.git/` | git 元数据 |
| `.env` / `*.log` | 本地配置与临时文件 |
| `__pycache__/` | Python 缓存 |
| 运行时数据目录（如 `browser_data`、`logs`、`htmlcov`） | 应走卷，不进镜像 |

**排障信号**：构建长时间卡在 `COPY . .` 或 `RUN chown -R` → 第一反应查 `.dockerignore` 是否存在且覆盖了 venv 与运行时数据目录。

### 3.6 按需构建，别一股脑全 build

```bash
docker compose build frontend   # 只改前端就只 build 前端
docker compose build backend    # 只改后端就只 build 后端
```

### 3.7 磁盘紧张才清缓存

```bash
docker buildx du                                   # 查看缓存占用
docker buildx prune --filter type=exec.cachemount  # 只清 cache mount
```

平时别清，清了下次又得重新下载。

### 3.8 构建管理纪律（关键，曾因违反导致引擎崩溃）

**构建是异步的：CLI 退出 ≠ 服务端停止。** Docker Desktop 的 `com.docker.build.exe` 是独立服务端进程，`docker compose build` 命令（CLI）即使被取消/退出，服务端仍可能在后台继续构建。

**血案**：曾因取消构建后未确认服务端已停，又重复发起多个 `docker compose build`，多个构建抢 BuildKit 锁互相阻塞，最后用 `taskkill //PID <com.docker.build.exe> //F` 强杀服务端进程，**直接导致 Docker 引擎崩溃，被迫重启电脑**。

#### 绝对禁止

| ❌ 禁止 | ✅ 正确 |
|--------|--------|
| `taskkill` 强杀 `com.docker.build.exe` | `docker buildx stop <builder>` 优雅停止 |
| 并发开多个 `docker compose build` 同一服务 | 一次只开一个构建，等它返回再发起下一个 |
| 取消 Bash 工具调用就以为构建停了 | 取消后用 `docker buildx ls` 确认 builder 状态 |
| 查 buildkit **容器**判断是否在构建 | Docker Desktop 用内置 builder，不创建独立容器，查容器永远查不到 |

#### 正确停止/确认构建状态

```bash
# 看哪个 builder 在用、是否活跃
docker buildx ls

# 优雅停止某 builder 的构建（不要 taskkill）
docker buildx stop <builder-name>

# 确认缓存占用稳定（不再变化=没有构建在跑）
docker buildx du
```

#### 崩溃恢复流程（若已发生引擎崩溃）

1. 重启 Docker Desktop（或重启电脑，视严重程度）
2. `docker info` 确认引擎恢复
3. `docker buildx prune -f` 清掉崩溃可能损坏的半成品缓存（可能较慢，21GB 级别要等几分钟，**不要中途取消**）
4. `docker buildx du` 确认缓存占用降到合理值（只剩不可回收部分）
5. 重新构建（首次会重新下载，之后命中 CACHED）

#### 关于 docker-mcp

Docker 官方提供 **MCP Toolkit**（`docker mcp` 命令），内置 `docker` cli 工具、catalog、gateway 等。它走官方 API 通道，状态反馈更好。但它本质仍封装 docker cli，**不能改变"构建异步"的本质**——避免崩溃的关键是纪律（不并发、不 taskkill），不是换工具。

确认 docker-mcp 是否可用：

```bash
docker mcp tools list       # 列出可用工具（含 docker cli 工具）
docker mcp --version
```

---

## 四、多环境配置：挂载 vs 构建

用户常问"下载官方镜像 + 挂载代码"和"构建代码"的区别——本质是"代码/依赖是塞进镜像，还是运行时从外面塞进去"。

### 4.1 两种模式对比

| 维度 | 挂载代码（Bind Mount） | 构建代码（COPY 进镜像） |
|------|----------------------|----------------------|
| 做法 | 拉官方/已构建镜像 + `volumes: ./src:/app` | `COPY . .` 把代码烤进镜像 |
| 改代码 | 立即生效，重启即可 | 需重新 build |
| 依赖 | 镜像需自带，或运行时现装 | 镜像自包含 |
| 可移植性 | 依赖宿主机有源码 | 拷到任何机器都能跑 |
| 环境一致性 | 依赖宿主机环境 | 100% 一致 |
| 适用 | **开发环境** | **生产环境** |

### 4.2 关键细节（易误解）

开发模式 compose 挂载 `./src:/app` 后，**运行时用的是挂载进来的代码，不是镜像里 COPY 的代码**。因此：

> 改业务代码不必重建镜像，重启即可；只有改依赖才需重新 build。

### 4.3 开发环境 vs 生产环境速查

| 场景 | 模式 | 数据持久化 |
|------|------|-----------|
| 开发 | 官方/已构建镜像 + Bind Mount（热重载） | 可用 Bind Mount 直接看 |
| 生产 | 完整构建镜像（代码烤进去） | 严格用 Named Volume |
| CI/测试 | 完整构建镜像（复现生产） | 无状态 |

### 4.4 前端 dev 模式改造（高频场景：把构建式前端改成挂载式 dev server）

后端天然适合挂载（`python main.py` 直接跑源码），前端则不同——构建式前端是 `vite build` → 静态文件烤进 nginx。要把前端也改成挂载开发，有四个必做的坑点：

**① 用 `docker-compose.override.yml` 而非改原 compose**

override 文件与 `docker-compose.yml` 同目录同名会被 `docker compose up` 自动合并，生产能力完整保留：

```bash
docker compose up                                       # 开发：自动加载 override
docker compose -f docker-compose.yml up --no-override   # 生产：不加载 override
```

**② 端口冲突用 `!override` 整体替换**

compose 对 list 是"追加去重"，override 里写 `6211:5173` 不会替换原 `6211:80`，会两条并存导致同宿主端口冲突。用 `!override` 标签整体替换（需 compose v2.24+）：

```yaml
services:
  frontend:
    ports: !override
      - "6211:5173"   # dev server 5173 替换原 nginx 80
```

`!reset` 是清空（不留新值），`!override` 是替换（带新值），这里要 `!override`。

**③ node_modules 必须用匿名卷隔离**

挂载 `./frontend:/app` 会把宿主机（Windows）的 `node_modules` 覆盖镜像内（Linux）装的，而 Windows 装的 esbuild/rollup 二进制在 Linux 容器跑不起来。用匿名卷隔离：

```yaml
volumes:
  - ./frontend:/app
  - /app/node_modules   # 匿名卷保护镜像内装的依赖，宿主机的进不来
```

匿名卷首次挂载时会从镜像对应路径拷贝内容，故镜像内 `npm install` 装的依赖会被保留。

**④ dev server 的 API 代理目标必须改服务名（高频坑）**

vite.config 里 `proxy.target: 'http://localhost:8000'` 在容器内指向 dev server 自己，会 502。改成读环境变量，dev 容器内设为 `backend:8000`（服务名）：

```ts
// vite.config.ts
proxy: {
  '/api': {
    target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
    // ...
  }
}
// 同时设 server.host: '0.0.0.0'，否则容器外访问不到
```

```yaml
# docker-compose.override.yml
environment:
  VITE_BACKEND_URL: http://backend:8000
```

**⑤ dev 模式对 Node 版本比生产构建更敏感（非显然坑）**

生产 Dockerfile 用 `node:18-alpine` 跑 `vite build` 可能一直正常，但改成 dev 模式跑 `npm run dev` 时会报 `The "paths[0]" argument must be of type string. Received undefined`（出在 unplugin-vue-components 加载阶段）。

根因：新版 `unplugin-vue-components@32` / `unplugin-auto-import@21` 需要 Node 20+，但生产构建路径对 node 版本容忍度高没暴露问题，dev server 加载插件时才触发。

**对策**：dev 用 `node:20-alpine`（与生产 Dockerfile 的 node 版本解耦，dev 可更高）。这也符合"Node 18 已停止维护，20 是当前 LTS"的规范。

**⑥ 完整 override 模板**

```yaml
# docker-compose.override.yml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev      # node 镜像 + cache mount 装依赖 + npm run dev
    ports: !override
      - "6211:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules             # 隔离，保护镜像内依赖
    environment:
      VITE_BACKEND_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_started    # 不用等 healthy，dev server 独立工作
```

---

## 五、规范化审查（Dockerfile/Compose 审查清单）

修改或创建 Docker 相关文件时，确保遵循：

### 5.1 极简镜像
- 优先 `alpine` / `slim` 系列基础镜像
- 用 `.dockerignore` 排除无关文件（见 3.5）
- 能多阶段构建就多阶段（编译产物拷进运行镜像，丢弃编译工具链）

### 5.2 构建加速
- 必须为 apt/pip/npm 配置中国区镜像源（见 references 模板）
- 依赖层在代码层之前（见 3.2）
- 配 cache mount（见 3.3）

### 5.3 安全排除
- 严禁镜像包含大型压缩包、敏感密钥（`.env`、`.git`）、平台二进制（`.exe`）

### 5.4 非 root 运行（核心安全实践）
推荐在 Dockerfile 创建并切换至非特权用户：

```dockerfile
RUN adduser -D -H -s /sbin/nologin appuser && \
    chown -R appuser:appuser /app
USER appuser
```

### 5.5 多阶段构建（需编译项目必用）

```dockerfile
FROM node:20-alpine AS builder
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

---

## 六、进阶可靠性建议

| 项 | 建议 |
|----|------|
| **健康检查** | 在 Compose 或 Dockerfile 定义 `HEALTHCHECK`，Docker 自动检测并重启异常容器 |
| **时区同步** | 容器内统一 `Asia/Shanghai`（`ENV TZ=Asia/Shanghai` + 装 tzdata） |
| **优雅停机** | 应用响应 `SIGTERM`，无损停止（避免 `kill -9` 丢数据） |
| **日志外发** | 日志输出到 `stdout/stderr`，宿主机统一收集，不要写容器内文件 |
| **重启策略** | `restart: unless-stopped` |

---

## 七、交互准则

- **简洁明了**：给具体代码片段，少讲冗长理论
- **主动规避风险**：发现 Dockerfile 里 `COPY` 大压缩包、缺 `.dockerignore`、缺 cache mount，主动提出优化
- **构建纪律（硬规则）**：绝不并发发起多个 `docker compose build` 同一服务；需要停止构建用 `docker buildx stop`，**绝不** `taskkill` 强杀 `com.docker.build.exe`（会致引擎崩溃）；发起构建前用 `docker buildx ls` 确认无活跃构建
- **中文回复**：所有建议和注释用中文

---

## 参考文档

| 文件 | 说明 |
|------|------|
| [deployment-guide.md](references/deployment-guide.md) | Docker 部署通用指南：Dockerfile 最佳实践模板、国内镜像源、构建缓存配置（含 cache mount 与跨项目共用）、Nginx 反代及 Compose 编排参考 |

## 速记口诀

> 开发挂载、生产构建；改代码重启、改依赖才 build；依赖层在前代码层在后；`.dockerignore` 必须有；`--progress plain` 看缓存；cache mount 自动兜底。
>
> **构建纪律**：构建异步，CLI 退出≠服务端停止；一次一个构建不并发；停用 `buildx stop`，绝不 `taskkill` 杀 `com.docker.build.exe`；崩溃后重启 + `buildx prune` 清损坏缓存。
