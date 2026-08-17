# wakita-governance 子智能体生成/模型注入脚本

wakita-governance 的三个子智能体（scout / auditor / builder）自 v2.4.0 起不再随插件分发（插件下无 `agents/` 目录），改为由本脚本把插件内置模板（`templates/agents/wakita-*.md`）渲染后写入**用户级 subagent 目录** `~/.zcode/agents/`，frontmatter 注入 `model:` 与 `thoughtLevel:`。

- 首次运行 = 初始化生成三个子智能体
- 后续运行 = 切换 model / thoughtLevel（覆盖写，写前备份 `.bak`）

ZCode 不在 agent frontmatter 中展开环境变量，因此切换 provider/model 需通过本脚本（或 `/subagent-create` 命令）注入真实值。

## 脚本作用

读取 `templates/agents/wakita-{scout,builder,auditor}.md` 三个模板，替换 frontmatter 的 `model:` 为 `custom:<provider>:<model-id>` 真实值（可选覆盖 `thoughtLevel:`），写入 `~/.zcode/agents/` 同名文件。

- 模板按脚本自身相对路径定位（`../templates/agents/`），仓库态与插件安装态结构一致，无需指定版本目录
- 写前备份已存在的目标文件为 `.bak`
- 幂等：目标文件内容已一致则跳过，重复运行不出错
- 校验 provider/model 在 `~/.zcode/v2/config.json` 中真实存在，不存在则列出可选项并退出
- 同时支持 `provider` 为 dict（当前 ZCode）和 list（旧版兜底）两种结构
- 写入 UTF-8 无 BOM，保留模板的换行风格（LF/CRLF）

## 用法

```bash
# 列出所有可用的 provider 和 model（默认排除不可用项：未启用 / 无 API Key）
python scripts/inject-agent-model.py --list

# 含不可用的 provider 一起列出（排查 "为什么看不到某 provider" 时用）
python scripts/inject-agent-model.py --list --all

# dry-run（默认 DeepSeek deepseek-v4-flash）：只打印计划，不写盘
python scripts/inject-agent-model.py

# 生成/更新到 ~/.zcode/agents/（默认 DeepSeek flash + 模板默认 thoughtLevel）
python scripts/inject-agent-model.py --apply

# 切换到其他 provider/model
python scripts/inject-agent-model.py --provider "builtin:bigmodel-coding-plan" --model GLM-5.2 --apply

# 覆盖思考强度（默认取模板值 max）
python scripts/inject-agent-model.py --thought-level high --apply
```

> 💡 **关于可用性过滤**：`--list` / `--json` 默认只返回「可用」的 provider（`enabled: true` **且** API Key 非空）。ZCode 客户端里部分内置 provider（GLM 官方、Z.ai 等）虽然 `enabled: true` 但未填入 API Key，会被隐藏。直连传参（`--provider <key> --model <id>`）不走此过滤，便于切换到刚开通但尚未重启客户端的 provider。查看全部加 `--all`。

> ⚠️ **关于 thoughtLevel**：合法档位由模型元数据决定（ZCode 客户端不硬编码枚举），`max` 已在 deepseek-v4-flash/pro 上验证可用。填了模型不支持的档位，运行时派agent会报「不支持的 task 思考强度」。

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--provider` | `466f2f41-bacb-4168-b493-d0afa32a0357`（DeepSeek） | config.json 中 `provider.<key>` 的 `<key>` |
| `--model` | `deepseek-v4-flash` | 所选 provider 下 `models.<key>` 的 `<key>` |
| `--thought-level` | 模板值（`max`） | 覆盖 frontmatter 的 `thoughtLevel:` |
| `--list` | - | 列出可用 provider+model 后退出（人类可读表格） |
| `--json` | - | 列出可用 provider+model 后退出（JSON，供 `/subagent-create` 命令解析） |
| `--all` | - | `--list`/`--json` 时连同不可用 provider 一起列出 |
| `--apply` | - | 实际写入；不加则为 dry-run，只打印计划 |

Provider key 中的 `:` 会被自动 URL 编码为 `%3A`（如 `builtin:bigmodel-coding-plan` -> `builtin%3Abigmodel-coding-plan`），最终写入值形如 `model: "custom:builtin%3Abigmodel-coding-plan:GLM-5.2"`。

dry-run 输出中 `files[].state` 含义：`missing`（将新建）/ `will_update`（将覆盖并备份）/ `identical`（已一致，跳过）。

## 路径说明

脚本读写的路径（自动定位，无需手动指定）：

| 路径 | macOS / Linux | Windows |
|------|--------------|---------|
| 模板目录（只读） | `<插件目录>/templates/agents/` | 同左 |
| 写入目标 | `~/.zcode/agents/` | `%USERPROFILE%\.zcode\agents\` |
| config.json | `~/.zcode/v2/config.json` | `%USERPROFILE%\.zcode\v2\config.json` |

## 回滚

每个已存在的目标文件写前都会生成 `.bak` 备份。如需回滚：

```bash
# macOS/Linux 示例
cp ~/.zcode/agents/wakita-scout.md.bak ~/.zcode/agents/wakita-scout.md

# Windows PowerShell 示例
Move-Item ~\.zcode\agents\wakita-scout.md.bak ~\.zcode\agents\wakita-scout.md -Force
```

## 生效方式

ZCode 当前不支持热重载已加载的 agent。写入后需**关闭并重开会话**（或重启 ZCode 客户端），新会话的 Agent 工具列表才会出现/更新这三个子智能体。

## 跨平台说明

本脚本用 Python 实现（3.10+），macOS / Linux / Windows 均可直接运行。`provider` 字段为 list 结构（旧版 ZCode）的情况也已兼容，避免在 Windows 上因结构差异报"provider not found"。

---

# Codex 子智能体注入脚本（inject-codex-agents.py）

Codex 不识别 ZCode 的 `~/.zcode/agents/*.md` 与 `commands/*.md`（协议差异详见 `docs/codex-子智能体方案.md`）。本脚本把同一套 scout/builder/auditor 角色渲染为 **Codex 原生 TOML agent**（`~/.codex/agents/`），并把三个 ZCode 斜杠命令替换为 **Codex 自定义提示词**（`~/.codex/prompts/`）。

> 注意：自定义提示词官方已标记 deprecated，且仅在 Codex CLI / IDE 扩展中显示；桌面 App 不显示 `/wakita-*`，请直接调遣 `@wakita-*` agent 或让主智能体执行对应脚本。

## 用法

```bash
# 查看生效配置（各 agent 取模板默认：scout/builder flash+high，auditor pro+max；~/.codex/config.toml 值仅展示）
python scripts/inject-codex-agents.py --json

# 人类可读的计划（不落盘）
python scripts/inject-codex-agents.py --list

# dry-run（不落盘）
python scripts/inject-codex-agents.py

# 实际写入 ~/.codex/agents/（3 个 TOML）与 ~/.codex/prompts/（3 个提示词）
python scripts/inject-codex-agents.py --apply

# 三个 agent 统一换模型 / 推理强度 / 沙箱
python scripts/inject-codex-agents.py --model deepseek-v4-pro --apply
python scripts/inject-codex-agents.py --reasoning max --apply
python scripts/inject-codex-agents.py --sandbox read-only --apply

# 只装 agent，不装提示词
python scripts/inject-codex-agents.py --no-prompts --apply
```

## 行为

- 模板目录：`templates/codex-agents/wakita-*.toml` 与 `templates/codex-prompts/wakita-*.md`（按脚本自身相对路径定位）
- 写入目标：`~/.codex/agents/` 与 `~/.codex/prompts/`（尊重 `$CODEX_HOME`，自动创建）
- `--model` 会对照 `~/.codex/models.json` 校验，不存在则报错并列出可用模型
- 写前备份已存在的目标文件为 `.bak`；幂等（内容一致则跳过）
- **不修改 `~/.codex/config.toml`**：Codex standalone TOML agent 自动发现，无需注册
- 写入 UTF-8 无 BOM，保留模板换行风格

## 参数

| 参数 | 说明 |
|------|------|
| `--model <slug>` | 三个 agent 统一模型（缺省保留模板每角色默认） |
| `--reasoning <档位>` | `model_reasoning_effort`（如 `high`/`max`） |
| `--sandbox <模式>` | 统一沙箱：`read-only` / `workspace-write` / `danger-full-access` |
| `--no-prompts` | 跳过提示词安装 |
| `--json` / `--list` | 只读输出（不落盘） |
| `--apply` | 实际写入；不加则 dry-run |

## 回滚

```bash
# 把 .bak 覆盖回目标文件，或直接删除 ~/.codex/agents/wakita-*.toml、~/.codex/prompts/wakita-*.md
```

## 生效方式

新开会话（或重启 Codex App / CLI）后可用 `@wakita-scout`、`@wakita-builder`、`@wakita-auditor` 调遣；CLI 中提示词显示为 `/wakita-subagent-create`、`/wakita-audit`、`/wakita-lock`。
