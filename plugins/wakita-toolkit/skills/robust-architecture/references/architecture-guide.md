# 项目架构与开发规范指南 (Refined)

本文档旨在为项目开发者提供一套健壮、可维护且易于扩展的通用架构规范。我们遵循 **KISS (Keep It Simple, Stupid)** 原则与 **关注点分离 (Separation of Concerns)**。

---

## 1. 核心目录结构 (Core Project Structure)

建议采用语义清晰、职责分明的分层结构。此结构适用于 Node.js, Python, Go 等多种技术栈。

```text
/project-root
├── /web-ui (or /frontend) # 前端源代码
├── /api-server (or /backend) # 后端业务逻辑
├── /db                    # 数据库迁移、Schema、种子数据
├── /data                  # 静态存储、上传文件、本地持久化数据 (.gitignore)
├── /logs                  # 运行时日志 (.gitignore)
├── /tools                 # 自动化脚本、运维工具、CI/CD 辅助
├── /docs                  # 设计文档、API 规范、部署手册
├── /tests                 # 集成测试、端对端测试 (E2E)
├── /config (or .env)      # 环境变量与应用配置
├── Dockerfile             # 容器定义
└── docker-compose.yml     # 容器编排
```

---

## 2. 前端开发规范 (Frontend)

前端应保持"轻薄"，主要承担展示逻辑与交互增强。

### 2.1 结构化路径
*   `components/`: **无状态**原子组件 (Button, Input)。
*   `features/`: 按**领域**划分的业务模块 (Auth, Dashboard)，包含该模块特有的逻辑。
*   `services/`: 数据请求层。禁止在组件内直接使用 Fetch/Axios。
*   `store/`: 全局状态管理 (Redux, Pinia, Context)。
*   `utils/`: 格式化、算法等纯工具函数。

### 2.2 健壮性原则
*   **API 抽象化**: 所有接口请求必须在服务层定义，支持请求拦截与统一错误处理。
*   **防御性编程**: 对后端返回的深嵌套对象进行判空或设置默认值。
- **环境隔离**: 使用环境变量管理不同环境 (Dev/Staging/Prod) 的 API 地址。

---

## 3. 后端开发规范 (Backend)

后端应专注于业务流程的严密性与数据的安全性。

### 3.1 分层职责
1.  **Controller (接入层)**: 参数校验 (Validation)、封装标准响应。
2.  **Service (业务层)**: 核心逻辑、事务流转。
3.  **Model/Repository (持久层)**: 数据库操作、ORM 定义。

### 3.2 API 标准化 (Standardization)
所有接口应返回统一的"信封"格式：
```json
{
  "success": true,
  "code": 200,      // 业务状态码
  "data": { ... },  // 成功时的数据
  "message": "...", // 提示信息
  "error": null     // 失败时的错误详情
}
```

### 3.3 API 设计最佳实践
*   **版本控制**: 路由前缀包含版本号 (如 `/api/v1/...`)。
*   **幂等性**: 对创建 (POST) 等操作考虑去重机制。

---

## 4. 数据库与数据管理 (DB & DATA)

### 4.1 `/db`：Schema 演进
*   使用 **Migrations**: 结构变更必须记入代码库，支持版本回滚。
*   **Schema as Code**: 数据库表结构应通过代码定义和更新，严禁手动修改生产环境。

### 4.2 `/data`：存储与隔离
*   **本地开发隔离**: 开发过程产生的临时文件应存放在 `/data/tmp` 等被 git 忽略的子目录。
*   **权限控制**: 生产环境挂载的 DATA 卷应设置严格的读写权限。

---

## 5. 日志与工具 (LOGS & TOOLS)

### 5.1 日志规范 (`/logs`)
*   **轮转与清理 (Rotation & Retention)**：配置日志按天或按大小切分，并设置保留策略（如仅保留最近 30 天或固定数量的文件），定期清理旧日志防止磁盘占满。
*   **上下文注入**: 日志应包含 `Trace-Id`，便于跨服务追踪。

### 5.2 自动化脚本 (`/tools`)
任何复杂或重复的操作应脚本化：
*   `deploy.sh`: 环境部署。
*   `backup_db.sh`: 数据库自动备份。
*   `test.sh`: 一键运行全量测试。
*   `monitor.sh`: 系统健康检查与资源监控。
*   `cleanup.sh`: 清理临时文件或旧日志。
*   `update.sh` / `rollback.sh`: 版本平滑升级与故障回退。

---

## 6. 用户、权限与安全 (USER)

*   **Auth (身份认证)**: 使用成熟的 JWT 或 OIDC 方案。
*   **RBAC (基于角色的权限控制)**: 权限控制应在后端 Service 层强制校验，前端仅做 UI 引导。
*   **Secret Management**: 敏感密钥 (DB 密码, API Key) 禁止提交至 Git。使用 Secret Manager 或容器环境变量注入。

---

## 7. 协作与交付规范 (New)

### 7.1 Git 工作流
*   **分支模型**: `main` (生产), `dev` (开发), `feature/*` (功能), `fix/*` (紧急修复)。
*   **Commit Message**: 遵循 `type: description` 规范 (如 `feat: add auth service`)。

### 7.2 容器化 (Docker)
*   **多阶段构建**: 减小生产环境镜像体积，排除构建工具。
*   **非 Root 运行**: 容器内进程应以普通用户运行，增加安全性。

---

## 8. 健壮性自查表 (Robustness Checklist)

- [ ] 所有输入是否过校验？
- [ ] 关键业务是否有数据库事务保护？
- [ ] 敏感配置是否已脱敏？
- [ ] 错误日志是否包含足够的上下文？
- [ ] 是否具备一键回滚能力？

遵循规范，是为了让代码在一年后依然清晰，在压力下依然稳定。
