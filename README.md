# wakita-plugins

Akita 自托管的 ZCode 插件仓库 —— 双插件架构，管控与工具分离。

## 架构

```
wakita-plugins
├── wakita-governance（管控核心 v2.8.0）    ← 行为约束层
│   ├── 危险操作拦截（PreToolUse）
│   ├── 审计留痕（PostToolUse）
│   ├── 工作规范注入（UserPromptSubmit）
│   ├── 子智能体模板（scout / auditor / builder / ace，由 /subagent-create 生成用户级 agent）
│   ├── Codex 子智能体模板（TOML × 4，由 inject-codex-agents.py 生成）
│   ├── 命令（/audit / /lock / /subagent-create）
│   ├── 1 个 skill（using-wakita：spec/plan/brainstorm 工作流编排）
│   └── scripts（inject-agent-model.py 生成/切换 ZCode 用户级子智能体；inject-codex-agents.py 生成 Codex 子智能体 + 命令提示词）
│
    └── wakita-toolkit（开发工具包 v1.9.0）     ← 领域知识层
        └── 38 个 skill（MySQL / Docker / 测试 / 前端 / 架构 / 运维 / 清理房间审查…）
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

每次提交 prompt 时注入 9 条规范提示（含大模块完成后加载 `clean-home` 做结构审查）。

#### 🤖 子智能体（4 个，用户级生成）

- `wakita-scout` - 代码库探索专家（只读，编码前侦察现有结构）
- `wakita-auditor` - 代码审查员（对照规范查问题，带文件:行号证据）
- `wakita-builder` - 代码实现专家（按 Spec/Plan 写代码 + 自验证）
- `wakita-ace` - 攻坚专家（常规手段失效或严重 Bug 多次复现时，做证据链根因分析与最小变更方案设计）

自 v2.4.0 起插件不再随包分发 agent，首次使用运行 `/subagent-create` 把模板渲染写入 `~/.zcode/agents/`（frontmatter 含 `model:` + `thoughtLevel:` + `injectAgentsMd:`），重开会话后可调遣，用户可自由编辑。

四个 agent 统一采用「结果回传协议」，向主智能体回传状态/产出物/验证结果/关键决策/依赖与风险/下一步建议，`partial` 不得谎报为 `success`。

**Codex 用户**：ZCode 的 `/subagent-create` 与 `~/.zcode/agents/` 在 Codex 下不可用（协议不兼容）。运行 `python plugins/wakita-governance/scripts/inject-codex-agents.py --apply` 生成 Codex 原生子智能体（`~/.codex/agents/wakita-*.toml`）与命令提示词（`~/.codex/prompts/`），详见 [docs/codex-子智能体方案.md](docs/codex-子智能体方案.md)。提示词已 deprecated 且仅 CLI/IDE 显示，桌面 App 直接调遣 `@wakita-*` agent 或让主智能体执行脚本即可；插件 hooks 在 Codex 下信任后同样生效。

#### 📚 内置 skill（1 个）

`using-wakita` - 任务分级与子智能体调度规范

#### 🔧 命令

- `/audit [行数]` - 查看最近审计日志
- `/lock <文件路径>` - 临时加锁保护文件
- `/subagent-create` - 交互式生成/切换四个用户级子智能体（scout/auditor/builder/ace）的运行模型与思考强度

> ⚠️ 以上命令为 ZCode 协议；Codex 下请使用 `inject-codex-agents.py --apply` 安装的 `/wakita-subagent-create`、`/wakita-audit`、`/wakita-lock` 提示词（已 deprecated，仅 CLI/IDE 显示；桌面 App 直接用 `@wakita-*` agent 或自然语言调用脚本）。

##### `/subagent-create` 命令详解

子智能体以用户级文件存在于 `~/.zcode/agents/`，frontmatter 的 `model:` / `thoughtLevel:` 需注入真实值（ZCode 不展开环境变量）。`/subagent-create` 首次运行即生成四个子智能体，后续运行用于切换 model / thoughtLevel。两种用法：

| 用法 | 说明 | 适用场景 |
|------|------|----------|
| `/subagent-create` | 交互式：读取本机 `~/.zcode/v2/config.json`，用 `AskUserQuestion` 列出可用 provider/model 供选择，dry-run 确认后写入 | 不熟悉 config.json 结构，或想可视化挑选（推荐） |
| `/subagent-create <provider> <model>` | 直连模式：跳过选择，直接注入指定 provider+model | 已在别处查过 provider key，或要注入默认列表里被过滤掉的 provider |

**交互式流程**：列出已启用 provider → 选 model → dry-run 展示计划 → 确认后写入 `~/.zcode/agents/` 四个 agent 文件（已有文件写前自动备份 `.bak`）→ 提示生效方式。

**provider 过滤规则**：交互式默认只列出 `enabled: true` 的 provider，未启用的（如未填 API Key 的 GLM 官方 API、未开通的 Kimi）会被自动排除，避免选了无法调用的 provider。需要查看全部（含未启用）时，直连模式不受此限制，或手动跑脚本加 `--all`。

> ⚠️ **生效方式**：ZCode 当前无热重载/重置会话功能（关注官方更新），写入后需**关闭并重开当前会话**或**重启 ZCode 客户端**才能生效。
>
> ⚠️ **插件升级提示**：升级至 v2.4.0 后插件级 `wakita-governance:wakita-*` agent 自动消失，仅保留用户级版本。

进阶用法（直接跑脚本，适合 CI/脚本化场景）见 [`scripts/README.md`](plugins/wakita-governance/scripts/README.md)，命令完整执行规范见 [`commands/subagent-create.md`](plugins/wakita-governance/commands/subagent-create.md)。

#### ⚙️ 安装后配置脚本（命令行直连）

除 `/subagent-create` 命令外，也可直接跑 `inject-agent-model.py` 脚本，适合 CI/脚本化场景或已知 provider key 的用户：

```bash
# 列出已启用的 provider/model（默认排除未启用项；加 --all 看全部）
python plugins/wakita-governance/scripts/inject-agent-model.py --list

# 生成/切换到指定 provider/model（先 dry-run 确认，再加 --apply 写入 ~/.zcode/agents/）
python plugins/wakita-governance/scripts/inject-agent-model.py --provider <key> --model <id>
python plugins/wakita-governance/scripts/inject-agent-model.py --provider <key> --model <id> --apply

# 覆盖思考强度（默认取模板值 max）
python plugins/wakita-governance/scripts/inject-agent-model.py --thought-level high --apply

# 输出 JSON 供程序解析（CI/脚本化场景）
python plugins/wakita-governance/scripts/inject-agent-model.py --json
```

跨平台 Python，同时支持 config.json 中 `provider` 为 dict / list 两种结构。详见 `scripts/README.md`。

##### Codex 注入脚本

```bash
# 查看配置并安装（dry-run 后加 --apply 落盘）
python plugins/wakita-governance/scripts/inject-codex-agents.py --json
python plugins/wakita-governance/scripts/inject-codex-agents.py --apply
```

把四个角色渲染为 `~/.codex/agents/wakita-{scout,builder,auditor,ace}.toml`（Codex 原生 TOML agent），并把命令提示词安装到 `~/.codex/prompts/`。幂等、写前 `.bak` 备份、不修改 `~/.codex/config.toml`。

---

### wakita-toolkit - 开发工具包

#### 📚 内置 skill（38 个）

| Skill | 用途 |
|-------|------|
| `ai-code-failure-modes` | AI 生成代码特有失败模式（stub 冒充/快乐路径/幻觉 API/配置未验证） |
| `brainstorm` | 创作性头脑风暴（画图、对比方案，只思考不写代码） |
| `canvas-interaction-space` | Canvas/WebGL 与 DOM 叠加层错位、屏幕像素 vs 模型空间交互规范 |
| `cd-deploy-verification` | CD 部署验证、回滚后诊断与部署事故边界（healthy ≠ deployed） |
| `chinese-commit-messages` | git commit message 强制中文 |
| `chinese-technical-writing` | 中文技术表达（spec/排障汇报/错误提示/代码注释） |
| `clean-home` | 清理房间：大模块结构审查编排入口（只路由，按步骤加载领域 skill） |
| `code-annotation` | 代码输出中文标注（变量名/函数名首次出现处附加翻译） |
| `code-reuse-audit` | 代码冗余审查与重构 |
| `code-structure-metrics` | 代码结构量化审查（硬编码/超长/理解困难/耦合） |
| `compose-cd-deploy-pitfalls` | Docker Compose CD 部署三类隐蔽陷阱与修复范式 |
| `config-sync-guard` | 跨环境同步可在线编辑配置的守卫流程（防覆盖用户新编辑/破坏性 DB 操作） |
| `display-source-normalization` | 多数据源展示模型 + 适配器规范化（渲染层禁来源分支） |
| `docker-compose-prod-default` | Docker Compose 生产/开发默认语义规范 |
| `docker-expert` | Docker 构建/部署最佳实践（含镜像源测试、超时预估） |
| `external-integration-doc` | 对外接口对接文档写作（契约交付物，禁止内部行话） |
| `frontend-dashboard-layout-spec` | 看板类页面布局与信息架构（观察窗口 > 统计报表） |
| `idempotent-migration` | 多步 DDL 迁移幂等守卫与大表锁窗 |
| `maxscript-pitfalls` | 3ds Max MaxScript 坑点指南 |
| `mysql-binlog-recovery` | MySQL binlog 前行镜像数据恢复流程 |
| `mysql-expert` | MySQL 表设计/索引/EXPLAIN/事务死锁/迁移规范 |
| `one-way-sync-antipattern` | 单向同步反模式审查（设计 vs 实现偏差检测） |
| `operate-through-channels` | 通过正确渠道修复：修代码不修数据 / 公开接口操作 / 端到端验证 |
| `param-refactor-semantic-audit` | 参数统一改造逐点语义审查（防机械批量加参数回归） |
| `playwright-cookie-injection-pitfalls` | Playwright cookie 注入持久化与浏览器会话排障 |
| `plugin-creator` | 创建/脚手架 ZCode 插件 |
| `production-config-sync` | 生产配置关联检查（改代码后检查 nginx/docker/CI 等关联配置是否需同步） |
| `project-baseline` | 项目基线检查（10 项最低交付底线） |
| `project-compliance-check` | 项目合规筛查（28 项生产前检查） |
| `pyinstaller-packaging` | Python 项目打包 .exe |
| `robust-architecture` | 分层架构/API 规范/目录结构/响应模型兜底 |
| `root-cause-no-patch` | 禁止临时补丁，必须定位根因 |
| `schema-migration-convergence` | 数据库迁移收敛（支持 7 种技术栈） |
| `silent-failure-audit` | 静默失败链路与展示层指标失真审计 |
| `spec-alignment-review` | 实现与 spec/需求对齐审查（偏离/假设/范围蔓延） |
| `taxonomy-normalization` | 分类字段批量归一化（label→code / 同义词 / 跨类组合） |
| `test-quality-principles` | 测试质量铁律与验证证据真实性 |
| `vue2-elementui-standards` | Vue2 + ElementUI 响应式组件与 CSS 令牌标准 |

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
│   ├── wakita-governance/         # 管控核心 v2.8.0
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── hooks/                 # 拦截/留痕/注入脚本
│   │   ├── templates/agents/      # 4 个子智能体模板（不注册为插件 agent）
│   │   ├── templates/codex-agents/    # Codex 版子智能体模板（TOML × 4）
│   │   ├── templates/codex-prompts/   # Codex 命令提示词模板（.md × 3）
│   │   ├── skills/                # 1 个 skill（using-wakita）
│   │   ├── commands/              # audit / lock / subagent-create 命令
│   │   └── scripts/               # inject-agent-model.py（ZCode）+ inject-codex-agents.py（Codex）
│   └── wakita-toolkit/            # 开发工具包 v1.9.0
│       ├── .claude-plugin/
│       │   └── plugin.json
        │       └── skills/                # 38 个领域 skill
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
