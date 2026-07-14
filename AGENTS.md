# AGENTS.md — wakita-plugins

## 仓库用途

ZCode（Claude Code 兼容）自托管插件仓库，提供 AI 开发工具的行为管控。

## 目录结构

```
wakita-plugins/
├── .claude-plugin/marketplace.json   # marketplace 声明（插件注册入口）
├── plugins/wakita-governance/        # 管控插件本体（v1.0.4）
│   ├── hooks/                        # PreToolUse / PostToolUse / UserPromptSubmit
│   ├── agents/                       # 子智能体：scout(探索) / auditor(审查) / builder(实现)
│   ├── skills/                       # 13 个 skill（见下文）
│   └── commands/                     # audit / lock 命令
├── docs/                             # 操作手册
└── AGENTS.md
```

## 内置 skill（13 个）

| Skill | 用途 |
|-------|------|
| `chinese-commit-messages` | git commit message 强制中文 |
| `code-reuse-audit` | 代码冗余审查与重构 |
| `docker-expert` | Docker 构建/部署最佳实践 |
| `frontend-dashboard-layout-spec` | 看板类页面 CSS 布局规范 |
| `maxscript-pitfalls` | 3ds Max MaxScript 坑点指南 |
| `mysql-expert` | MySQL 数据库设计/SQL 优化 |
| `operate-through-channels` | 通过正确渠道修复：修代码不修数据 / 通过公开接口操作 / 验证必须端到端 |
| `plugin-creator` | 创建/脚手架 ZCode 插件 |
| `pyinstaller-packaging` | Python 项目打包 .exe |
| `robust-architecture` | 分层架构/API 规范/目录结构 |
| `root-cause-no-patch` | 禁止临时补丁，必须定位根因 |
| `test-quality-principles` | 测试质量四条铁律：先读实现再写测试 / 测行为不测实现 / 失败路径必测 / Mock 依赖不 Mock 被测对象 |
| `using-wakita` | 任务分级与子智能体调度规范 |

## 内置子智能体

- `wakita-scout` — 编码前探索现有结构（只读）
- `wakita-auditor` — 代码审查，带文件:行号证据
- `wakita-builder` — 按 Spec/Plan 实现代码 + 自验证

## 内置命令

- `/audit [行数]` — 查看最近审计日志
- `/lock <文件路径>` — 临时加锁保护文件

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

## 文档

- `docs/docker操作手册.md` — Docker 相关操作指南
- `docs/git操作手册.md` — Git 操作指南

## 注意事项

- 本仓库无标准构建系统（无 pyproject.toml / package.json）
- `audit.log` 和 `rules.protected.json` 被 .gitignore 排除，仅本地生效
- 所有修改必须命中 plugin 目录下的实际文件才能生效（根目录文件仅 AGENTS.md 和 marketplace.json 是源头）
- 主分支为 `main`，禁止强制推送（由 PreToolUse hook 保障）
