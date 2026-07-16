---
name: docker-expert
description: 提供 Docker 构建缓存复用、部署规范审查、多环境配置及问题诊断。涵盖 BuildKit 缓存挂载、镜像优化、Compose 编排、镜像源测试与超时优化。触发词：docker build、构建镜像、构建太慢、构建缓存、Dockerfile、docker-compose、容器化、前端容器化、Vite dev server、HMR 不生效、docker buildx、构建卡住、镜像源、pull timeout、拉取超时。
---

# Docker 专家技能 (Docker Expert Skill)

## 一、构建缓存机制（核心：让构建从"分钟级"降到"秒级"）

Docker 构建有**双层缓存**：

- **BuildKit 层缓存**：Dockerfile 每行 RUN/COPY 是一层，指令不变则日志显示 `CACHED`，零耗时。改 `COPY . .`（应用代码）只击穿该层及之后，依赖层不受影响。
- **BuildKit 缓存挂载（cache mount）**：通过 `--mount=type=cache` 将下载内容持久化到宿主机独立区域，对应 RUN 层失效重跑时从本地缓存读取，不联网。

判断缓存命中必须加 `--progress plain`：`CACHED` = 层命中；秒级完成但无下载 = cache mount 兜底；出现大量下载+分钟级耗时 = 未命中。

详细机制（缓存存储位置、跨项目共用策略、击穿场景表格）见 `references/deployment-guide.md`。

## 二、加速构建实操清单

1. **改业务代码时根本别 build**：挂载模式下运行时用的是挂载进来的代码，不是镜像里 COPY 的代码。改业务代码只需 `docker compose restart <service>`；只有改依赖才需重新 build。
2. **必须构建时保证缓存自动命中**：Dockerfile 里依赖层必须在代码层之前（`COPY requirements.txt` 在前，`COPY . .` 在后）。
3. **cache mount 务必配上**：模板见 `references/deployment-guide.md` 2.2 节。`sharing=locked` 表示并发构建串行访问同一 cache mount，避免损坏。
4. **`.dockerignore` 必须有**（最易踩的坑，曾致构建卡死 13 分钟）：缺失会导致本地 `venv`(947MB)、`browser_data`(77MB)、docs(20MB) 全被 `COPY . .` 拷进上下文，`chown -R` 改这 1GB+ 文件属主卡死。必排除 `venv/`、`node_modules/`、`dist/`、`.git/`、`.env`、`__pycache__/`、运行时数据目录。排障信号：构建长时间卡在 `COPY . .` 或 `RUN chown -R` -> 第一反应查 `.dockerignore`。
5. **按需构建，别一股脑全 build**：`docker compose build frontend` 只改前端就只 build 前端。
6. **磁盘紧张才清缓存**：平时别清，清了下次又得重新下载。

### 构建管理纪律（关键，曾因违反导致引擎崩溃）

**构建是异步的：CLI 退出 ≠ 服务端停止。** Docker Desktop 的 `com.docker.build.exe` 是独立服务端进程。

**绝对禁止**：`taskkill` 强杀 `com.docker.build.exe`（应改用 `docker buildx stop <builder>` 优雅停止）；并发开多个 `docker compose build` 同一服务；取消 CLI 就以为构建停了（取消后用 `docker buildx ls` 确认 builder 状态）。

正确停止/确认：`docker buildx ls`（看 builder 状态）；`docker buildx stop <builder-name>`（优雅停止）；`docker buildx du`（缓存占用稳定即无构建在跑）。

**崩溃恢复**（若已发生引擎崩溃）：1) 重启 Docker Desktop 2) `docker info` 确认引擎恢复 3) `docker buildx prune -f` 清掉可能损坏的半成品缓存 4) `docker buildx du` 确认占用正常 5) 重新构建。

## 三、多环境配置：挂载 vs 构建

| 维度 | 挂载代码（Bind Mount） | 构建代码（COPY 进镜像） |
|------|----------------------|----------------------|
| 做法 | 拉官方/已构建镜像 + `volumes: ./src:/app` | `COPY . .` 把代码烤进镜像 |
| 改代码 | 立即生效，重启即可 | 需重新 build |
| 依赖 | 镜像需自带，或运行时现装 | 镜像自包含 |
| 可移植性 | 依赖宿主机有源码 | 拷到任何机器都能跑 |
| 环境一致性 | 依赖宿主机环境 | 100% 一致 |
| 适用 | **开发环境** | **生产环境** |

关键细节：开发模式 compose 挂载 `./src:/app` 后，运行时用的是挂载进来的代码，不是镜像里 COPY 的代码。开发环境速查：开发用官方/已构建镜像 + Bind Mount（热重载），生产用完整构建镜像（代码烤进去）+ Named Volume，CI/测试用完整构建镜像（复现生产、无状态）。

### 前端 dev 模式改造（高频场景）

把构建式前端（`vite build` → 静态文件烤进 nginx）改成挂载式 dev server（HMR 即时生效）。配置三件套：`Dockerfile.dev`（node:20-slim + cache mount）+ `docker-compose.override.yml`（挂载源码 + 匿名卷隔离 + `shm_size: 1gb`）+ `vite.config.ts`（`host: 0.0.0.0` + 代理目标用服务名）。三大坑（esbuild 崩溃、504 Outdated Optimize Dep、组件命名冲突）与完整排错方案见 `references/examples.md`。

## 四、规范化审查（Dockerfile/Compose 审查清单）

修改或创建 Docker 相关文件时，确保遵循：

1. **极简镜像**：优先 `alpine`/`slim` 系列；用 `.dockerignore` 排除无关文件；能多阶段构建就多阶段。
2. **构建加速**：必须为 apt/pip/npm 配置中国区镜像源（模板见 `references/deployment-guide.md`）；依赖层在代码层之前；配 cache mount。
3. **安全排除**：严禁镜像包含大型压缩包、敏感密钥（`.env`、`.git`）、平台二进制（`.exe`）。
4. **非 root 运行**（核心安全实践）：在 Dockerfile 创建并切换至非特权用户。
5. **多阶段构建**（需编译项目必用）：完整模板见 `references/deployment-guide.md`。

## 五、进阶可靠性

健康检查（`HEALTHCHECK`）、时区同步（`Asia/Shanghai`）、优雅停机（响应 `SIGTERM`）、日志外发（`stdout/stderr`）、重启策略（`restart: unless-stopped`），详见 `references/deployment-guide.md`。

## 六、镜像源优化与超时管理

### 镜像源测试

**问题**：国内网络访问 Docker Hub 不稳定，拉取镜像慢或超时。

**解决方案**：先测试镜像源可用性，再配置最优源。

```bash
# 运行镜像源测试脚本
bash scripts/test-docker-mirrors.sh
```

**脚本功能**：
- 测试官方源 + 9 个国内镜像源的连通性
- 测量每个源的响应速度（ms）
- 按速度排序输出可用镜像源
- 生成 daemon.json 配置推荐

**测试结果示例**：
```
可用镜像源（按响应速度排序）：

  ✓ 阿里云
    地址: registry.cn-hangzhou.aliyuncs.com
    响应: 156ms | 速度评级: 极快

  ✓ 腾讯云
    地址: mirror.ccs.tencentyun.com
    响应: 203ms | 速度评级: 快
```

**配置方法**：将测试结果中最快的 3 个源添加到 Docker daemon 配置：

```json
{
  "registry-mirrors": [
    "https://registry.cn-hangzhou.aliyuncs.com",
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

### 镜像大小预估与超时设置

**问题**：大型镜像拉取时间长，默认超时导致拉取中断。

**解决方案**：预估镜像大小，根据网速计算合理超时时间。

```bash
# 预估镜像拉取时间
bash scripts/estimate-pull-time.sh nginx:latest
bash scripts/estimate-pull-time.sh python:3.11-slim
bash scripts/estimate-pull-time.sh pytorch/pytorch:latest
```

**脚本功能**：
- 测试当前网络速度（MB/s）和延迟（ms）
- 获取目标镜像大小
- 预估拉取时间
- 推荐超时设置（预估时间 × 2）
- 生成 Docker Compose 超时配置示例

**预估结果示例**：
```
预估结果：

  镜像大小:         187 MB
  当前网速:         2.5 MB/s
  网络延迟:         45 ms
  预估拉取时间:     75 秒
  推荐超时时间:     150 秒
```

**超时配置**：

```yaml
# docker-compose.yml
services:
  app:
    image: nginx:latest
    deploy:
      restart_policy:
        delay: 5s
        max_attempts: 3
        window: 120s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 150s
      retries: 3
      start_period: 60s
```

**环境变量设置**：
```bash
# Linux/macOS
export DOCKER_CLIENT_TIMEOUT=150
export COMPOSE_HTTP_TIMEOUT=150

# Windows (PowerShell)
$env:DOCKER_CLIENT_TIMEOUT="150"
$env:COMPOSE_HTTP_TIMEOUT="150"
```

### 常见镜像大小参考

| 镜像 | 大小 | 预估拉取时间（2MB/s） |
|------|------|----------------------|
| hello-world | 13 KB | <1 秒 |
| alpine:3.19 | 7 MB | 4 秒 |
| node:20-slim | 90 MB | 45 秒 |
| python:3.11-slim | 130 MB | 65 秒 |
| nginx:latest | 187 MB | 94 秒 |
| ubuntu:22.04 | 77 MB | 39 秒 |
| postgres:16 | 410 MB | 205 秒 |
| pytorch/pytorch:latest | 2.3 GB | 19 分钟 |

### 最佳实践

1. **先测试再配置**：使用 `test-docker-mirrors.sh` 测试当前网络环境
2. **预估再拉取**：使用 `estimate-pull-time.sh` 预估大型镜像拉取时间
3. **配置多个源**：daemon.json 配置 3 个以上镜像源作为备用
4. **合理设置超时**：大型镜像超时设置为预估时间的 2 倍
5. **定期测试**：网络环境变化时重新测试镜像源

## 六、交互准则

- **简洁明了**：给具体代码片段，少讲冗长理论
- **主动规避风险**：发现 Dockerfile 里 `COPY` 大压缩包、缺 `.dockerignore`、缺 cache mount，主动提出优化
- **构建纪律（硬规则）**：绝不并发发起多个 `docker compose build` 同一服务；需要停止构建用 `docker buildx stop`，**绝不** `taskkill` 强杀 `com.docker.build.exe`（会致引擎崩溃）；发起构建前用 `docker buildx ls` 确认无活跃构建
- **中文回复**：所有建议和注释用中文

## 参考文档

- [deployment-guide.md](references/deployment-guide.md) - Docker 部署通用指南：Dockerfile 模板、国内镜像源、缓存配置、Nginx 反代、Compose 编排
- [examples.md](references/examples.md) - 跨项目 cache mount 共用、前端 dev 模式改造完整示例

## 速记口诀

> 开发挂载、生产构建；改代码重启、改依赖才 build；依赖层在前代码层在后；`.dockerignore` 必须有；`--progress plain` 看缓存；cache mount 自动兜底。
>
> **构建纪律**：构建异步，CLI 退出≠服务端停止；一次一个构建不并发；停用 `buildx stop`，绝不 `taskkill` 杀 `com.docker.build.exe`；崩溃后重启 + `buildx prune` 清损坏缓存。
