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
- **前端容器化**：Vite/dev server 在 Docker 内崩溃、HMR 不生效、504 错误、前端 Dockerfile.dev 配置

---

## 二、构建缓存机制（核心：让构建从"分钟级"降到"秒级"）

### 2.1 双层缓存模型

Docker 构建有**两层缓存**，理解清楚才能定位"为什么又重新下载了"。

**第 1 层：BuildKit 层缓存（RUN/COPY 层命中 -> 显示 `CACHED`）** -- Dockerfile 每一行 `RUN`/`COPY` 是一层，Docker 记下每层结果。只要该行指令没变，下次构建直接复用上一次的成果，日志显示 `CACHED`，零耗时零下载。改了 `COPY . .`（应用代码）只有该层及之后失效；装依赖的层只要指令不变则 `CACHED`，不重新下。

**第 2 层：BuildKit 缓存挂载（cache mount -> 层失效也兜底，关键提速手段）** -- 通过 `--mount=type=cache` 把"下载的东西"持久化到宿主机独立区域。即使对应 RUN 层失效重跑，下载内容仍从本地缓存读，不联网。典型挂载目标见下表：

| 挂载目标 | 持久化内容 | 典型体积 |
|---------|-----------|---------|
| `/var/cache/apt` + `/var/lib/apt` | apt 的 .deb 包 | 数百 MB |
| `/root/.cache/pip` | pip wheel 包（numpy/torch 等重依赖） | ~1GB |
| `~/.npm` 或 pnpm store | npm/pnpm 包 | 数百 MB |
| 浏览器二进制缓存目录 | chromium/playwright 二进制 | 数百 MB |

### 2.2 缓存存到哪了 / 如何共用

默认存在 Docker 内部存储区（Linux 在 `/var/lib/docker/buildkit/` 下；Docker Desktop 在 WSL2 ext4 虚拟盘内部，不暴露给宿主）。每个 cache mount 按"工作目录 + id"隔离，可用 `docker buildx du` 查看占用、`docker buildx prune` 清理。

cache mount 的"共用率"分两种：同一项目多次构建自动共用（无需配置）；跨项目共用同一份官方依赖缓存默认隔离，需显式给相同 `id` 才能共用。跨项目共用写法见 `references/examples.md`。

### 2.3 如何判断缓存是否命中

构建时**必须加 `--progress plain`**（`docker compose build <service> --progress plain`），否则看不到每层状态。日志判读：`CACHED` 表示层缓存命中零耗时零下载；某层秒级完成但无下载表示 cache mount 兜底生效；某层出现大量下载加分钟级耗时表示缓存未命中，需排查。

### 2.4 哪些改动会击穿缓存

| 改动 | 影响范围 | cache mount 是否兜底 |
|------|---------|---------------------|
| 应用代码变动（`COPY . .`） | 仅该层及之后 | 不涉及下载，无需兜底 |
| Dockerfile 任意 `RUN` 指令变动 | 该层及之后全部重跑 | 兜住下载 |
| `requirements.txt`/`package.json` 变动 | 依赖层重跑 | 只下新增包 |
| 切换基础镜像（`FROM`） | 几乎全部重跑 | 兜住，但系统级包可能需重下 |

最大优势：应用代码变动只击穿最后的 `COPY` 层，依赖层完全不受影响--这是把 Dockerfile 分层写对的核心收益。

---

## 三、加速构建实操清单

1. **改业务代码时根本别 build**：挂载模式下运行时用的是挂载进来的代码，不是镜像里 COPY 的代码。改业务代码只需 `docker compose restart <service>`；只有改依赖（pip 包、apt 包、浏览器二进制）才需重新 build。
2. **必须构建时保证缓存自动命中**：Dockerfile 里依赖层必须在代码层之前（`COPY requirements.txt` 在前，`COPY . .` 在后）。
3. **cache mount 务必配上**：模板见 `references/deployment-guide.md` 2.2 节。`sharing=locked` 表示并发构建串行访问同一 cache mount，避免损坏。
4. **`.dockerignore` 必须有**（最易踩的坑，曾致构建卡死 13 分钟）：缺失会导致本地 `venv`(947MB)、`browser_data`(77MB)、docs(20MB) 全被 `COPY . .` 拷进上下文，`chown -R` 改这 1GB+ 文件属主卡死。必排除 `venv/`、`node_modules/`、`dist/`、`.git/`、`.env`、`__pycache__/`、运行时数据目录。排障信号：构建长时间卡在 `COPY . .` 或 `RUN chown -R` -> 第一反应查 `.dockerignore`。
5. **按需构建，别一股脑全 build**：`docker compose build frontend` 只改前端就只 build 前端。
6. **磁盘紧张才清缓存**：平时别清，清了下次又得重新下载。
7. **构建管理纪律（关键，曾因违反导致引擎崩溃）**：见下方专节。

### 3.8 构建管理纪律（关键，曾因违反导致引擎崩溃）

**构建是异步的：CLI 退出 ≠ 服务端停止。** Docker Desktop 的 `com.docker.build.exe` 是独立服务端进程，`docker compose build` 命令即使被取消/退出，服务端仍可能在后台继续构建。曾因取消构建后未确认服务端已停，又重复发起多个 `docker compose build`，多个构建抢 BuildKit 锁互相阻塞，最后用 `taskkill //PID <com.docker.build.exe> //F` 强杀服务端进程，**直接导致 Docker 引擎崩溃，被迫重启电脑**。

**绝对禁止**：`taskkill` 强杀 `com.docker.build.exe`（应改用 `docker buildx stop <builder>` 优雅停止）；并发开多个 `docker compose build` 同一服务；取消 Bash 工具调用就以为构建停了（取消后用 `docker buildx ls` 确认 builder 状态）；查 buildkit 容器判断是否在构建（Docker Desktop 用内置 builder，不创建独立容器，查容器永远查不到）。

正确停止/确认构建状态：`docker buildx ls`（看哪个 builder 在用、是否活跃）；`docker buildx stop <builder-name>`（优雅停止）；`docker buildx du`（确认缓存占用稳定即无构建在跑）。

**崩溃恢复流程**（若已发生引擎崩溃）：1) 重启 Docker Desktop（或重启电脑）2) `docker info` 确认引擎恢复 3) `docker buildx prune -f` 清掉崩溃可能损坏的半成品缓存（21GB 级别要等几分钟，不要中途取消）4) `docker buildx du` 确认占用降到合理值 5) 重新构建（首次会重新下载，之后命中 CACHED）。

**关于 docker-mcp**：Docker 官方 MCP Toolkit（`docker mcp`）状态反馈更好，但本质仍封装 docker cli，不能改变"构建异步"的本质--避免崩溃靠纪律（不并发、不 taskkill），不是换工具。

---

## 四、多环境配置：挂载 vs 构建

用户常问"下载官方镜像 + 挂载代码"和"构建代码"的区别--本质是"代码/依赖是塞进镜像，还是运行时从外面塞进去"。

| 维度 | 挂载代码（Bind Mount） | 构建代码（COPY 进镜像） |
|------|----------------------|----------------------|
| 做法 | 拉官方/已构建镜像 + `volumes: ./src:/app` | `COPY . .` 把代码烤进镜像 |
| 改代码 | 立即生效，重启即可 | 需重新 build |
| 依赖 | 镜像需自带，或运行时现装 | 镜像自包含 |
| 可移植性 | 依赖宿主机有源码 | 拷到任何机器都能跑 |
| 环境一致性 | 依赖宿主机环境 | 100% 一致 |
| 适用 | **开发环境** | **生产环境** |

关键细节：开发模式 compose 挂载 `./src:/app` 后，运行时用的是挂载进来的代码，不是镜像里 COPY 的代码。因此改业务代码不必重建镜像，重启即可；只有改依赖才需重新 build。开发环境速查：开发用官方/已构建镜像 + Bind Mount（热重载），生产用完整构建镜像（代码烤进去）+ Named Volume，CI/测试用完整构建镜像（复现生产、无状态）。

### 前端 dev 模式改造（高频场景）

把构建式前端（`vite build` → 静态文件烤进 nginx）改成挂载式 dev server（HMR 即时生效）。

**配置三件套**：`Dockerfile.dev`（node:20-slim + cache mount）+ `docker-compose.override.yml`（挂载源码 + 匿名卷隔离 + `shm_size: 1gb`）+ `vite.config.ts`（`host: 0.0.0.0` + 代理目标用服务名）。

**三大坑**（必知）：
- esbuild `The service was stopped` → slim 镜像 + 升级 esbuild + shm_size
- `504 Outdated Optimize Dep` → 样式全量引入，关闭按需
- 组件命名冲突 → 重命名文件，不绕别名

详情含 Dockerfile.dev 模板、三个坑的完整排错方案、排错速查表、Playwright 控制台验证——见 `references/examples.md`。

---

## 五、规范化审查（Dockerfile/Compose 审查清单）

修改或创建 Docker 相关文件时，确保遵循：

1. **极简镜像**：优先 `alpine`/`slim` 系列；用 `.dockerignore` 排除无关文件；能多阶段构建就多阶段（编译产物拷进运行镜像，丢弃编译工具链）。
2. **构建加速**：必须为 apt/pip/npm 配置中国区镜像源（模板见 `references/deployment-guide.md`）；依赖层在代码层之前；配 cache mount。
3. **安全排除**：严禁镜像包含大型压缩包、敏感密钥（`.env`、`.git`）、平台二进制（`.exe`）。
4. **非 root 运行**（核心安全实践）：在 Dockerfile 创建并切换至非特权用户。
5. **多阶段构建**（需编译项目必用）：完整模板见 `references/deployment-guide.md`。

---

## 六、进阶可靠性建议

涉及健康检查（`HEALTHCHECK`）、时区同步（`Asia/Shanghai`）、优雅停机（响应 `SIGTERM`）、日志外发（`stdout/stderr`）、重启策略（`restart: unless-stopped`），详见 `references/deployment-guide.md`。

## 七、交互准则

- **简洁明了**：给具体代码片段，少讲冗长理论
- **主动规避风险**：发现 Dockerfile 里 `COPY` 大压缩包、缺 `.dockerignore`、缺 cache mount，主动提出优化
- **构建纪律（硬规则）**：绝不并发发起多个 `docker compose build` 同一服务；需要停止构建用 `docker buildx stop`，**绝不** `taskkill` 强杀 `com.docker.build.exe`（会致引擎崩溃）；发起构建前用 `docker buildx ls` 确认无活跃构建
- **中文回复**：所有建议和注释用中文

---

## 参考文档

- [deployment-guide.md](references/deployment-guide.md) - Docker 部署通用指南：Dockerfile 模板、国内镜像源、缓存配置、Nginx 反代、Compose 编排
- [examples.md](references/examples.md) - 跨项目 cache mount 共用、前端 dev 模式改造完整示例

## 速记口诀

> 开发挂载、生产构建；改代码重启、改依赖才 build；依赖层在前代码层在后；`.dockerignore` 必须有；`--progress plain` 看缓存；cache mount 自动兜底。
>
> **构建纪律**：构建异步，CLI 退出≠服务端停止；一次一个构建不并发；停用 `buildx stop`，绝不 `taskkill` 杀 `com.docker.build.exe`；崩溃后重启 + `buildx prune` 清损坏缓存。
