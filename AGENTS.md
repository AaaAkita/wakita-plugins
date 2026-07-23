# AGENTS.md — wakita-plugins

## 仓库用途

ZCode（Claude Code 兼容）自托管插件仓库，提供 AI 开发工具的行为管控与领域知识注入。

**双插件架构**：管控核心与开发工具包分离，可独立安装、维护和开关。

## 目录结构

```
wakita-plugins/
├── .claude-plugin/marketplace.json   # marketplace 声明（注册两个插件）
├── plugins/
│   ├── wakita-governance/            # 管控核心（v2.1.0）
│   │   ├── hooks/                    # PreToolUse / PostToolUse / UserPromptSubmit
│   │   ├── agents/                   # 子智能体：scout(探索) / auditor(审查) / builder(实现)，统一结果回传协议
│   │   ├── skills/                   # 1 个 skill：using-wakita
│   │   ├── commands/                 # audit / lock 命令
│   │   └── scripts/                  # inject-agent-model.py 子智能体模型切换
	│   └── wakita-toolkit/               # 开发工具包（v1.2.2）
	│       └── skills/                   # 16 个领域 skill（见下文）
├── docs/                             # 操作手册
└── AGENTS.md
```

## 插件一：wakita-governance（管控核心，v2.1.0）

提供危险操作拦截、写操作留痕、工作规范注入、子智能体调度与审计命令。

### 内置子智能体

- `wakita-scout` - 编码前探索现有结构（只读）
- `wakita-auditor` - 代码审查，带文件:行号证据
- `wakita-builder` - 按 Spec/Plan 实现代码 + 自验证

三个 agent 统一采用「结果回传协议」（`<result_protocol>` 章节），向主智能体回传状态/产出物/验证结果/关键决策/依赖与风险/下一步建议，`partial` 不得谎报为 `success`。

### 内置 skill（1 个）

| Skill | 用途 |
|-------|------|
| `using-wakita` | 任务分级与子智能体调度规范 |

### 内置命令

- `/audit [行数]` - 查看最近审计日志
- `/lock <文件路径>` - 临时加锁保护文件
- `/submodel` - 交互式切换三个子智能体的运行模型（读 config.json 列出可用项供用户选，注入后提示需重开会话生效）。支持直连模式 `/submodel <provider> <model>`。交互式默认只列出「可用」的 provider（`enabled: true` **且** API Key 非空），已启用但未填 Key 的内置 provider（如 GLM 官方、Z.ai）自动排除；直连模式不受此限。详见 `commands/submodel.md`。

### 安装后配置脚本

- `scripts/inject-agent-model.py` - 切换三个子智能体的 `model:` 字段。ZCode 不展开 agent frontmatter 里的环境变量，用户安装后若想换 provider/model 需跑此脚本。跨平台 Python，同时支持 config.json 中 `provider` 为 dict / list 两种结构。详见 `scripts/README.md`。

## 插件二：wakita-toolkit（开发工具包，v1.2.2）

领域 skill 集合，可按需独立开关。纯 skill 插件，不依赖外部 MCP 服务。

### 内置 skill（16 个）

| Skill | 用途 |
|-------|------|
| `chinese-commit-messages` | git commit message 强制中文 |
| `code-reuse-audit` | 代码冗余审查与重构 |
| `docker-expert` | Docker 构建/部署最佳实践（含镜像源测试、超时预估） |
| `frontend-dashboard-layout-spec` | 看板类页面 CSS 布局规范 |
| `maxscript-pitfalls` | 3ds Max MaxScript 坑点指南 |
| `mysql-expert` | MySQL 数据库设计/SQL 优化 |
| `operate-through-channels` | 通过正确渠道修复：修代码不修数据 / 公开接口操作 / 端到端验证 |
| `plugin-creator` | 创建/脚手架 ZCode 插件 |
| `project-baseline` | 项目基线检查（10 项最低交付底线） |
| `project-compliance-check` | 项目合规筛查（28 项生产前检查） |
| `pyinstaller-packaging` | Python 项目打包 .exe |
| `robust-architecture` | 分层架构/API 规范/目录结构 |
| `root-cause-no-patch` | 禁止临时补丁，必须定位根因 |
| `schema-migration-convergence` | 数据库迁移收敛（支持 7 种技术栈） |
| `test-quality-principles` | 测试质量四条铁律 |
| `vue2-elementui-standards` | Vue2 + ElementUI 响应式组件标准化 |

## Hook 协议规范

- 所有 hook：stdin 读 JSON → stdout 输出 JSON，始终 `exit 0`
- 阻断机制靠 `permissionDecision: "deny"`，不靠退出码
- 异常一律降级为 `systemMessage` 告警，不阻塞正常工作
- 审计日志写入 `hooks/audit.log`（被 .gitignore 排除）

## 编码约定

- **语言**：Python 3.10+（hooks）、Markdown（skills/agents/commands）
- **提交信息**：中文内容 + 英文类型前缀（如 `feat:`、`fix:`、`chore:`）
- **写操作留痕**：所有 Edit/Write/Bash 写操作自动记入 audit.log
- **危险拦截规则**：见 `hooks/rules.py` 的 `DANGEROUS_COMMANDS` 和 `DEFAULT_PROTECTED_FILES`
- **工作规范**：UserPromptSubmit 注入 6 条规范（中文提交/带行号证据/不臆测/危险拦截/复盘沉淀/分级动手）

## 版本更新规范（必须同时更新 4 处）

每次更新插件版本号时，必须同步更新以下文件，否则 ZCode 无法检测到新版本：

| # | 文件 | 更新内容 |
|---|------|----------|
| 1 | `plugins/<plugin>/.claude-plugin/plugin.json` | `version` 字段 |
| 2 | `.claude-plugin/marketplace.json` | 对应插件 `description` 中的版本号 |
| 3 | `plugins/<plugin>/agents/*.md` | 如有模型等配置变更 |
| 4 | `AGENTS.md` + `README.md` | 版本号、skill 列表等文档 |

**ZCode 更新检测机制**：读取 marketplace.json 中 description 的版本号，与已安装版本对比。版本号相同则不触发更新提示。

## 文档

- `docs/docker操作手册.md` — Docker 相关操作指南
- `docs/git操作手册.md` — Git 操作指南

## 注意事项

- 本仓库无标准构建系统（无 pyproject.toml / package.json）
- `audit.log` 和 `rules.protected.json` 被 .gitignore 排除，仅本地生效
- 所有修改必须命中 plugin 目录下的实际文件才能生效
- 主分支为 `main`，禁止强制推送（由 PreToolUse hook 保障）
