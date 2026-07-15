# wakita-plugins

Akita 自托管的 ZCode 插件仓库 —— 双插件架构，管控与工具分离。

## 架构

```
wakita-plugins
├── wakita-governance（管控核心 v2.0.0）    ← 行为约束层
│   ├── 危险操作拦截（PreToolUse）
│   ├── 审计留痕（PostToolUse）
│   ├── 工作规范注入（UserPromptSubmit）
│   ├── 子智能体（scout / auditor / builder）
│   ├── 命令（/audit / /lock）
│   └── 1 个 skill（using-wakita）
│
└── wakita-toolkit（开发工具包 v1.0.0）     ← 领域知识层
    └── 13 个 skill（MySQL / Docker / 测试 / 前端 / 架构…）
```

两个插件**独立安装、独立维护、独立开关**，互不依赖。

## 插件详情

### wakita-governance — 管控核心

#### 🛡️ 危险操作拦截（PreToolUse hook）

工具执行**前**拦截，命中即阻断：
- `rm -rf /`、`rm -rf ~`、`rm -rf C:\` 等根目录递归删除
- `git push --force` 到 main/master
- 裸 `git reset --hard`（无目标 commit）
- `DROP TABLE` / `DROP DATABASE` / `TRUNCATE TABLE`
- `chmod -R 777 /`、`mkfs`、fork bomb
- 编辑/写入受保护文件（`.env`、lock 文件、`.git` 配置等）

#### 📝 审计留痕与提交规范（PostToolUse hook）

- 所有 Edit/Write/Bash 写操作记入 `audit.log`
- `git commit` 校验 message 是否中文

#### 💬 工作规范注入（UserPromptSubmit hook）

每次提交 prompt 时注入 6 条规范提示。

#### 🤖 内置子智能体（3 个）

- `wakita-scout` — 代码库探索专家（只读，编码前侦察现有结构）
- `wakita-auditor` — 代码审查员（对照规范查问题，带文件:行号证据）
- `wakita-builder` — 代码实现专家（按 Spec/Plan 写代码 + 自验证）

#### 📚 内置 skill（1 个）

`using-wakita` — 任务分级与子智能体调度规范

#### 🔧 命令

- `/audit [行数]` — 查看最近审计日志
- `/lock <文件路径>` — 临时加锁保护文件

---

### wakita-toolkit — 开发工具包

#### 📚 内置 skill（13 个）

| Skill | 用途 |
|-------|------|
| `chinese-commit-messages` | git commit message 强制中文 |
| `code-reuse-audit` | 代码冗余审查与重构 |
| `docker-expert` | Docker 构建/部署最佳实践 |
| `frontend-dashboard-layout-spec` | 看板类页面 CSS 布局规范 |
| `maxscript-pitfalls` | 3ds Max MaxScript 坑点指南 |
| `mysql-expert` | MySQL 数据库设计/SQL 优化 |
| `operate-through-channels` | 通过正确渠道修复：修代码不修数据 / 公开接口操作 / 端到端验证 |
| `plugin-creator` | 创建/脚手架 ZCode 插件 |
| `pyinstaller-packaging` | Python 项目打包 .exe |
| `robust-architecture` | 分层架构/API 规范/目录结构 |
| `root-cause-no-patch` | 禁止临时补丁，必须定位根因 |
| `test-quality-principles` | 测试质量四条铁律 |
| `vue2-elementui-standards` | Vue2 + ElementUI 响应式组件标准化 |

---

## 安装

### 方式一：添加为 marketplace（推荐）

```bash
# 1. 添加 marketplace
/plugin marketplace add E:\software\wakita-plugins
# 或推到 GitHub 后用：
# /plugin marketplace add https://github.com/AaaAkita/wakita-plugins

# 2. 安装插件（可只装一个，也可都装）
/plugin install wakita-governance@wakita-plugins
/plugin install wakita-toolkit@wakita-plugins
```

### 方式二：直接挂载

将 `plugins/wakita-governance` 和/或 `plugins/wakita-toolkit` 复制到 `~/.zcode/cli/plugins/cache/wakita-plugins/` 对应目录，并在 `installed_plugins.json` 中登记。

## 目录结构

```
wakita-plugins/
├── .claude-plugin/
│   └── marketplace.json           # marketplace 声明（注册两个插件）
├── plugins/
│   ├── wakita-governance/         # 管控核心 v2.0.0
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── hooks/                 # 拦截/留痕/注入脚本
│   │   ├── agents/                # 3 个子智能体
│   │   ├── skills/                # 1 个 skill（using-wakita）
│   │   └── commands/              # audit / lock 命令
│   └── wakita-toolkit/            # 开发工具包 v1.0.0
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/                # 13 个领域 skill
├── docs/                          # 操作手册
└── README.md
```

## 自定义规则

### 修改危险命令黑名单

编辑 `plugins/wakita-governance/hooks/rules.py` 的 `DANGEROUS_COMMANDS` 列表。

### 修改默认保护文件

编辑 `rules.py` 的 `DEFAULT_PROTECTED_FILES` 列表。

运行时用 `/lock <文件>` 追加的文件存在 `hooks/rules.protected.json`（被 .gitignore 排除，仅本地生效）。

## 技术说明

- Hook 协议：stdin 读 JSON，stdout 输出 JSON，始终 `exit 0`。阻断靠 `permissionDecision: "deny"`，不靠退出码。
- 审计日志在 `hooks/audit.log`（被 .gitignore 排除）。
- 所有 hook 异常都降级为 `systemMessage` 告警，绝不阻塞正常工作。

## License

私有仓库，仅供本人使用。
