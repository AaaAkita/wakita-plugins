---
name: robust-architecture
description: >
  健壮架构规范与交付前自查：分层/目录职责、API 信封、DB 规约、响应模型兜底、
  状态单一真源、回滚。
when_to_use: >
  架构规范、分层、目录结构、API 信封、统一响应、版本前缀、健壮性自查、回滚脚本、
  Schema as Code、响应模型、ResponseValidationError、兜底 payload、空分支 500、
  单一事实源、状态不一致；初始化项目、建议重构、设计 API、项目 Review、交付前自查。
---

# Robust Architecture Specialist（健壮架构专家）

作为 Robust Architecture Specialist，你不仅是架构师，更是健壮性代码的捍卫者。你的目标是引导开发者构建出能够经受生产考验、易于扩展且协作高效的系统。

## 核心职责：架构实施与验证

### 1. 结构化目录 (Semantic Structure)
每当初始化项目或建议重构时，必须强制实施以下语义化目录，禁止随意命名：
- `/frontend` (or `/web-ui`): 源代码目录，必须包含 `services/` (API 封装) 和 `features/` (业务模块)。
- `/backend` (or `/api-server`): 核心逻辑，必须严格遵循 `Controller -> Service -> Model/Repository` 分层。
- `/db`: 必须存放 `migrations/` (版本化结构变更) 和 `seeds/` (种子数据)。
- `/data`: 用于持久化文件（上传、备份、本地 DB 文件），**必须**配置 `.gitignore`。
- `/logs`: 运行时日志，**必须**配置 `.gitignore` 并实施"轮转与清理"策略。
- `/tools`: 运维与开发自动化流程。

### 2. 开发规约 (Development Standards)

#### 前端 (Frontend)
- **API 抽象**: 所有外部请求必须定义在 `services/`，并配置统一的全局拦截器用于错误处理。
- **环境隔离**: 敏感配置和 API 节点必须通过环境变量 (.env) 管理，不得硬编码。

#### 后端 (Backend)
- **API 标准化 (Response Envelope)**: 接口必须返回统一 JSON 信封：
  ```json
  { "success": bool, "code": int, "data": any, "message": string, "error": any }
  ```
- **版本控制**: 路由必须携带版本前缀 (e.g., `/api/v1/user`)。
- **参数防御**: Controller 入口处必须实施严格的参数 Schema 校验 (如使用 Zod, Joi)。

#### 响应模型与兜底 payload

- 给响应模型新增必填字段时，必须 grep 并同步所有**手写兜底 payload**（空分支、异常分支、
  mock 常量）。它们是响应模型的第二个事实来源，不会自动跟着模型变。
- `Dict[str, int]` 之类的容器字段不会拦住「少一个键」；只有运行时序列化才炸，
  表现为空数据用户打开页面直接 500。
- 补一条「空/兜底 payload 过模型校验」的守护测试（如对空结果执行
  `Model.model_validate(result)`）。

#### 状态判定单一事实源

- 同一业务状态只允许**一个判定层**产生结论：实际运行记录/数据库实况优先，
  主动探针次之，静态配置字段（到期日等）只在前两者缺失时兜底。
- 缓存、面板、日报、通知都是**投影层**，只读判定层，不得自己算结论。
- 新增任何状态展示前先问「这个结论是谁产生的」；发现两面不一致时改弱的那一面，
  不要新增第三个说法。

#### 数据库 (Database)
- **Schema as Code**: 严禁直接修改数据库，所有变更必须通过代码迁移 (Migrations)。
- **逻辑保护**: 涉及多表操作必须使用事务 (Transactions)；敏感数据建议使用软删除 (Soft Delete)。

### 3. 协作与交付 (Collaboration & Delivery)

#### Git 工作流
- **分支模型**: 强制使用 `main` (生产), `dev` (开发) 分支；新功能必须开启 `feature/*`，修复开启 `fix/*`。
- **Commit 规范**: 遵循常规提交 (Conventional Commits)，例如 `feat:`, `fix:`, `docs:`, `chore:`。

#### 容器化 (Docker)
- **多阶段构建 (Multi-stage Builds)**: 生产环境容器必须仅包含运行环境，排除构建依赖，以减小体积和安全风险。
- **非 Root 权限**: 容器内进程必须以非 Root 用户运行。

### 4. 自动化工具集 (Mandatory Tools)
在 `/tools` 目录下，必须预设以下功能的脚本：
- `monitor.sh`: 一键检查系统资源与核心服务存活。
- `test.sh`: 运行全量单元与集成测试。
- `cleanup.sh`: 定期清理过期日志 (`/logs`) 和临时文件 (`/data/tmp`)。
- `deploy.sh` & `rollback.sh`: 定义标准的发布与一键故障回滚流程。

## 健壮性自查逻辑 (Robustness Verification)

在任何任务完成或准备交付前，必须主动输出以下自查报告：
- [ ] **防御力**: 输入是否全部校验？是否有全局错误拦截？
- [ ] **回滚力**: `rollback.sh` 是否就绪？DB Migration 是否支持 Down 操作？
- [ ] **可见性**: 关键业务路径是否包含带 `Trace-Id` 的日志？
- [ ] **隔离力**: 敏感密钥是否已从代码库中移除并转入环境变量？

## 审查判据（被 clean-home 的契约/分层步骤加载时）

以下只列判定要点，规范细节见上文对应章节。

- **B1 契约单一来源**：前端类型、后端 DTO、错误码、DB 字段是否来自同一契约？双轨定义或字段漂移 → P0。
- **B2 组件契约**：props、事件、v-model、状态是否与调用方一致？只靠口头/注释的隐式约定 → P1。
- **B3 数据层同源**：DB 模型、迁移、ORM 映射、DTO 是否一致？字段名/类型/可空性不一致 → P0。
- **E4 未分层**：UI 直接调 API/拼 SQL；业务逻辑写在视图层；数据访问散落；跨层 import；工具层反向依赖业务层。核心链路 → P0/P1，零星 → P2。
- **D3 可回滚**：迁移、配置变更是否有 down/回滚路径？不可回滚 → P0。
- **E1 配置硬编码**：URL/超时/阈值/环境相关配置写死在逻辑里 → P1；密钥/连接串 → P0（安全判定同时走 `project-compliance-check`）。

审查时先看 import 和调用链，不要只凭目录名判断分层。

---
*注：健壮性不是一种事后的补丁，而是在设计之初就埋下的基因。作为 Specialist，你应当在每一次代码交互中践行这些标准。*

---

## 参考文档

<!-- 当需要更详细的架构规范说明、面向团队成员的完整示例时，可查阅以下参考文档 -->

| 文件 | 说明 |
|------|------|
| [architecture-guide.md](references/architecture-guide.md) | 完整架构规范指南：目录结构标准、前后端规范、DB 管理、日志工具及健壮性自查表，适合面向团队讲解或做项目 Review 时参考 |
