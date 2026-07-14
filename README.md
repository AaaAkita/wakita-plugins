# wakita-plugins

Akita 自托管的 ZCode 插件仓库 —— 用于管控 AI 开发工具的行为。

提供**危险操作拦截**、**代码规范与提交管控**、**子智能体行为约束**三大能力，内置 3 个子智能体和 13 个 skill。

## 功能

### 🛡️ 危险操作拦截（PreToolUse hook）
工具执行**前**拦截，命中即阻断（`permissionDecision: deny`）：
- `rm -rf /`、`rm -rf ~`、`rm -rf C:\` 等根目录递归删除
- `git push --force` 到 main/master
- 裸 `git reset --hard`（无目标 commit）
- `DROP TABLE` / `DROP DATABASE` / `TRUNCATE TABLE`
- `chmod -R 777 /`、`mkfs`、`dd if=...of=/dev/`、fork bomb
- 编辑/写入受保护文件（`.env`、lock 文件、`.git` 配置等）

### 📝 代码规范与提交管控（PostToolUse hook）
工具执行**后**留痕与提醒（不阻断）：
- 所有 Edit/Write/Bash 写操作记入 `audit.log`
- `git commit` 校验 message 是否中文，非中文则提醒

### 💬 工作规范注入（UserPromptSubmit hook）
每次提交 prompt 时注入规范提示：
- commit message 必须中文
- 改动代码带「文件:行号」证据
- 不臆测、找不到明说
- 子智能体调用前先探索

### 🤖 内置子智能体（3 个）
- `wakita-scout` — 代码库探索专家（只读，编码前侦察现有结构）
- `wakita-auditor` — 代码审查员（对照项目规范查问题，带文件:行号证据）
- `wakita-builder` — 代码实现专家（按 Spec/Plan 写代码 + 自验证 + 配套单测）

### 📚 内置 skill（13 个）
mysql-expert、robust-architecture、chinese-commit-messages、docker-expert、code-reuse-audit、root-cause-no-patch、frontend-dashboard-layout-spec、pyinstaller-packaging、maxscript-pitfalls、operate-through-channels、plugin-creator、test-quality-principles、using-wakita

### 🔧 命令
- `/audit [行数]` — 查看最近审计日志
- `/lock <文件路径>` — 临时加锁保护文件

## 安装

### 方式一：添加为 marketplace（推荐）

在 ZCode 中添加本仓库为 marketplace，再安装插件：

```bash
# 1. 添加 marketplace（指向本地路径或 git 远端）
/plugin marketplace add E:\software\wakita-plugins
# 或推到 GitHub 后用：
# /plugin marketplace add https://github.com/AaaAkita/wakita-plugins

# 2. 安装插件
/plugin install wakita-governance@wakita-plugins
```

### 方式二：直接挂载到插件缓存目录

将 `plugins/wakita-governance` 复制到 `~/.zcode/cli/plugins/cache/wakita-plugins/wakita-governance/1.0.0/`，并在 `installed_plugins.json` 中登记。

## 目录结构

```
wakita-plugins/
├── .claude-plugin/
│   └── marketplace.json           # marketplace 声明
├── plugins/
│   └── wakita-governance/         # 管控插件本体
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── hooks/                 # 拦截/留痕/注入脚本
│       ├── agents/                # 3 个子智能体
│       ├── skills/                # 13 个 skill
│       └── commands/              # audit / lock 命令
├── docs/                          # 操作手册
└── README.md
```

## 自定义规则

### 修改危险命令黑名单
编辑 `plugins/wakita-governance/hooks/rules.py` 的 `DANGEROUS_COMMANDS` 列表，每条格式：
```python
(正则模式, "阻断原因"),
```

### 修改默认保护文件
编辑 `rules.py` 的 `DEFAULT_PROTECTED_FILES` 列表。

运行时用 `/lock <文件>` 追加的文件存在 `hooks/rules.protected.json`（被 .gitignore 排除，仅本地生效）。

## 技术说明

- Hook 协议：stdin 读 JSON，stdout 输出 JSON，始终 `exit 0`。阻断靠 `permissionDecision: "deny"`，不靠退出码。
- 审计日志在 `hooks/audit.log`（被 .gitignore 排除）。
- 所有 hook 异常都降级为 `systemMessage` 告警，绝不阻塞正常工作。

## License

私有仓库，仅供本人使用。
