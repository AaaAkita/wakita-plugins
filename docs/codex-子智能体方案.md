# Codex 子智能体方案（v2.5.0）

## 结论摘要

wakita 的 `/subagent-create`、`/audit`、`/lock` 在 Codex 下**不能直接使用，是因为命令注册协议不同**（ZCode 的 `commands/*.md` 斜杠命令，Codex 不注册）；但底层 hooks（拦截/审计/规范注入）**会被 Codex 加载并实际运行**。本方案提供 Codex 原生等价物，并修复了实测发现的三处 hooks 运行问题。

| 能力 | ZCode（原实现） | Codex（本方案） |
|------|----------------|-----------------|
| 子智能体定义 | `~/.zcode/agents/*.md`（frontmatter：`model`/`thoughtLevel`/`injectAgentsMd`） | `~/.codex/agents/*.toml`（`name`/`description`/`developer_instructions` + 可选 `model`/`model_reasoning_effort`/`sandbox_mode`） |
| 斜杠命令 | `plugins/wakita-governance/commands/*.md` + `${CLAUDE_PLUGIN_ROOT}` 展开 | `~/.codex/prompts/*.md`（frontmatter：`description`/`argument-hint`；官方已标记 deprecated，仅 CLI/IDE 显示） |
| 安装方式 | `/subagent-create` 或 `inject-agent-model.py` | `inject-codex-agents.py --apply` |
| hooks | `hooks/hooks.json`（PreToolUse/PostToolUse/UserPromptSubmit） | 同一份 `hooks.json`，Codex 加载并信任后即生效（本机已验证） |

角色正文（探索/实现/审查规范、结果回传协议）与 ZCode 版保持同一事实源，只改传输层。

## 一、诊断：为什么命令无法使用

### 1. 命令注册机制不同（主因）

ZCode 按 Claude Code 插件协议把 `commands/*.md` 注册为斜杠命令，并用 `${CLAUDE_PLUGIN_ROOT}` 占位符定位插件安装目录（[subagent-create.md](plugins/wakita-governance/commands/subagent-create.md) 第 28、191-192 行）。Codex **不注册 `commands/` 目录**，因此 `/subagent-create`、`/audit`、`/lock` 在 Codex 中根本不存在。Codex 侧等价物是「自定义提示词」`~/.codex/prompts/*.md`（本方案的 `/wakita-subagent-create`、`/wakita-audit`、`/wakita-lock`），但官方文档已将其标注 **deprecated**，且只在 **Codex CLI / IDE 扩展**中显示。桌面 App 里直接用自然语言让主智能体执行脚本，或调遣 `@wakita-*` agent。

### 2. 子智能体格式不同

ZCode 用户级 subagent 是 `~/.zcode/agents/*.md`，frontmatter 含 `model:`、`thoughtLevel:`、`injectAgentsMd:`（如 [wakita-scout.md](plugins/wakita-governance/templates/agents/wakita-scout.md) 第 5-7 行）。Codex 的自定义 agent 是 `~/.codex/agents/*.toml` 独立 TOML 文件，字段为 `name`/`description`/`developer_instructions`（官方文档 developers.openai.com/codex/subagents）。两边 schema 完全不同，ZCode 生成的文件 Codex 不识别。

### 3. hooks 实际在 Codex 运行，但有三个次生问题（v2.5.0 已修复）

**实测证据**：`~/.codex/config.toml` 存在 `[hooks.state."wakita-governance@wakita-plugins:hooks/hooks.json:..."]` 信任记录（hook 已被用户信任）；插件缓存 `~/.codex/plugins/cache/wakita-plugins/wakita-governance/<版本>/hooks/audit.log` 实时记录了当前 Codex 会话的工具调用。也就是说 Codex 会加载并执行插件 `hooks.json`，危险拦截、审计留痕、规范注入**实际生效**。

真正让「命令看似不可用 / 表现异常」的是三个次生问题（本次均已修复）：

1. **日志写到了插件缓存副本**：hook 从插件缓存目录运行，`audit.log` 写在缓存里；原 `/wakita-audit` 读仓库 `hooks/audit.log`（旧测试数据）→ 看不到新记录。
2. **lock 清单写错位置**：原 `/wakita-lock` 把 `rules.protected.json` 写进仓库，而运行中的 PreToolUse hook 读插件缓存副本 → 加锁不生效。
3. **Windows 编码乱码**：hook 脚本用 Python 默认代码页（本机 GBK）输出 JSON，Codex 按 UTF-8 解析 → UserPromptSubmit 注入的中文规范变乱码（本会话开头那段 `[wakita �����淶]` 就是它）。已在 4 个 hook 脚本中强制 stdin/stdout/stderr 为 UTF-8。

另发现：`/audit` 命令依赖 `audit.py read` 子命令，但原 `audit.py` 没有 `main()`，已补齐。

### 4. 附加发现：ZCode 脚本默认 provider 已过期（已修复）

`inject-agent-model.py` 的默认 provider 写死为 DeepSeek `466f2f41-...`（[inject-agent-model.py](plugins/wakita-governance/scripts/inject-agent-model.py) 第 59 行），但本机 `~/.zcode/v2/config.json` 中该 provider 已禁用/无 API Key（`usable: false`），当前可用的是 `opencode-go`（key `4ac42331-...`）。裸跑 `--apply` 会生成指向不可用 provider 的 agent。已加回退逻辑：默认 provider 不可用时自动落到第一个可用 provider（第 185 行起 `resolve_default_provider`）。

## 二、方案结构

```
plugins/wakita-governance/
├── templates/
│   ├── agents/                # ZCode 版（.md，保持不变）
│   ├── codex-agents/          # 新增：Codex 版（.toml × 3）
│   │   ├── wakita-scout.toml      # 只读探索，sandbox_mode = read-only
│   │   ├── wakita-builder.toml    # 实现 + 自验证，workspace-write
│   │   └── wakita-auditor.toml    # 代码审查，read-only，reasoning = max
│   └── codex-prompts/         # 新增：Codex 命令等价物（.md × 3）
│       ├── wakita-subagent-create.md
│       ├── wakita-audit.md
│       └── wakita-lock.md
├── hooks/                     # v2.5.0：4 个脚本补 UTF-8 强制；audit.py 补 CLI main()
└── scripts/
    └── inject-codex-agents.py # 新增：渲染模板 → ~/.codex/agents/ 与 ~/.codex/prompts/
```

设计要点：

- **Codex 原生字段**：`name`/`description`/`developer_instructions` 必填；`model`、`model_reasoning_effort`、`sandbox_mode`、`nickname_candidates` 可选。scout/auditor 直接声明 `sandbox_mode = "read-only"`，从沙箱层保证只读，比 ZCode 的工具白名单更强。
- **不碰 `~/.codex/config.toml`**：standalone TOML agent 自动发现，无需注册。
- **模型默认**：scout/builder `deepseek-v4-flash` + `high`，auditor `deepseek-v4-pro` + `max`（与 ZCode 模板的 flash/pro + thoughtLevel 对应）。模型不符本机 catalog 时脚本会报错并列出可用模型。

## 三、安装与使用

### 1. 生成子智能体 + 命令提示词

```bash
# 查看生效配置（默认模型/推理强度、目标目录）
python plugins/wakita-governance/scripts/inject-codex-agents.py --json

# dry-run 预览（不落盘）
python plugins/wakita-governance/scripts/inject-codex-agents.py

# 实际写入 ~/.codex/agents/ 与 ~/.codex/prompts/
python plugins/wakita-governance/scripts/inject-codex-agents.py --apply
```

可选参数：

| 参数 | 说明 |
|------|------|
| `--model <slug>` | 三个 agent 统一换模型（如 `deepseek-v4-pro`） |
| `--reasoning <档位>` | 换 `model_reasoning_effort`（如 `max`） |
| `--sandbox <模式>` | 统一换沙箱（`read-only`/`workspace-write`/`danger-full-access`） |
| `--no-prompts` | 只装 agent，不装命令提示词 |

### 2. 生效方式

新开会话（或重启 Codex App / 重开 CLI）后：

- 对话中直接调遣：`@wakita-scout`、`@wakita-builder`、`@wakita-auditor`；
- Codex CLI / IDE 扩展中提示词显示为 `/wakita-subagent-create`、`/wakita-audit`、`/wakita-lock`；⚠️ 官方已标记自定义提示词 deprecated，桌面 App 不显示，App 里直接让主智能体执行脚本或调遣 `@wakita-*`；
- 主智能体也可用 spawn/multi-agent 工具按同样角色提示派发（`using-wakita` skill 的「Codex 环境」章节有说明）。

### 3. 结果回传协议

三个 TOML agent 的 `developer_instructions` 均含 `<result_protocol>`：末尾必须附 `状态`（success/partial/failed）、`摘要`、`位置`、`阻塞项`、`根因`、`下一步建议`。主智能体按状态推进，`partial` 不得当 `success`。

## 四、hooks 现状（2026-08-17 实测）

Codex（桌面 App / CLI）加载并信任插件 `hooks/hooks.json` 后，以下能力**实际生效**：

- **PreToolUse**：危险命令拦截、保护清单拦截生效（清单 `rules.protected.json` 与运行中的 hook 同目录，位于插件缓存）。
- **PostToolUse**：写操作留痕生效，日志实时写入插件缓存 `~/.codex/plugins/cache/wakita-plugins/wakita-governance/<版本>/hooks/audit.log`；git commit 中文校验同样生效。
- **UserPromptSubmit**：工作规范注入生效（v2.5.0 修复 Windows 编码后不再乱码）。
- `/wakita-audit`、`/wakita-lock` 提示词已改为读写插件缓存副本，保证与运行中的 hook 一致。

注意：插件升级会替换缓存目录，缓存里的 `audit.log` / `rules.protected.json` 属本地运行数据，升级前如需保留请先备份。若后续想把运行数据统一放到 `~/.codex/` 下（如 `~/.codex/wakita/`），可另开 spec：让 `rules.py` / `audit.py` 支持环境变量覆盖路径，并让插件 hooks 与提示词共用该目录。

## 五、回滚

每次写入前，已存在的目标文件会先备份为 `.bak`：

```powershell
# 回滚单个 agent
Move-Item ~\.codex\agents\wakita-scout.toml.bak ~\.codex\agents\wakita-scout.toml -Force

# 回滚提示词
Move-Item ~\.codex\prompts\wakita-audit.md.bak ~\.codex\prompts\wakita-audit.md -Force
```

或直接删除 `~/.codex/agents/wakita-*.toml` 与 `~/.codex/prompts/wakita-*.md`（均为新增文件，不影响其他配置）。

## 六、与 ZCode 版的关系

- ZCode 侧（`templates/agents/*.md`、`commands/*.md`）**保持不动**，两套方案共存；hooks 脚本为两环境共用，v2.5.0 的 UTF-8/CLI 修复双方受益。
- 角色正文同一口径：Codex TOML 的 `developer_instructions` 与 ZCode MD 正文内容一致，仅载体不同；后续改角色规范需两处同步。
- Codex 侧官方依据：子智能体 developers.openai.com/codex/subagents；自定义提示词 learn.chatgpt.com/docs/custom-prompts。
