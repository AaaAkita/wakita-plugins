# Codex 子智能体支持（TOML agents + 命令替代 + 注入脚本）

**日期**: 2026-08-17
**状态**: 开发完成
**完成日期**: 2026-08-17
**关联**: [subagent-create-user-scope-agents.md](subagent-create-user-scope-agents.md)（ZCode 侧 v2.4.0，已完成）

## 摘要

Codex 不识别 ZCode 的 `~/.zcode/agents/*.md` 与 `commands/*.md` 斜杠命令，导致 wakita 三个命令和子智能体在 Codex 下不可用（底层 `hooks.json` 会被 Codex 加载运行，实测生效）。本 spec 为 Codex 提供原生方案：新增 `templates/codex-agents/*.toml`（Codex 自定义 agent，写入 `~/.codex/agents/`）、`templates/codex-prompts/*.md`（Codex 自定义斜杠命令，写入 `~/.codex/prompts/`）与注入脚本 `inject-codex-agents.py`，并更新文档与 using-wakita skill。顺带修复 `inject-agent-model.py` 默认 provider 过期与 hooks 在 Codex 下的路径/编码问题。

## 背景与目标

- 问题：用户已在 Codex（桌面 App / CLI）环境工作，但 wakita 的 `/subagent-create`、`/audit`、`/lock` 与 scout/builder/auditor 三角色均无法使用。根因是协议不兼容：ZCode 用 MD+frontmatter 定义 agent、用 `commands/*.md` 注册斜杠命令，Codex 不识别；但 `hooks.json` 会被 Codex 加载（信任后生效），实测拦截/审计/规范注入均在运行，命令"不可用"还叠加了日志/清单路径错位与 Windows 编码乱码两个次生问题。
- 目标：三角色以 Codex 原生 TOML agent 落地，保留「结果回传协议」；提供 Codex 版命令替代；脚本化安装（幂等 + `.bak` 备份），一次命令完成。
- 成功标准：`python scripts/inject-codex-agents.py --apply` 后 `~/.codex/agents/` 出现 3 个 TOML、`~/.codex/prompts/` 出现 3 个提示词；新会话可调遣；文档说明命令差异与 hooks 现状。

## 方案

- 新增 `templates/codex-agents/wakita-{scout,builder,auditor}.toml`：必填 `name`/`description`/`developer_instructions`；可选 `model`/`model_reasoning_effort`/`sandbox_mode`（scout、auditor 用 `read-only`，builder 用 `workspace-write`）。角色正文与 ZCode 版一致（只改传输层）。
- 新增 `scripts/inject-codex-agents.py`：读模板 → 可选 `--model/--reasoning/--sandbox` 覆盖 → dry-run/`--apply` → 写 `~/.codex/agents/`（默认同时装 prompts 到 `~/.codex/prompts/`，`--no-prompts` 关闭）→ `.bak` 备份 → 幂等。
- 新增 `templates/codex-prompts/*.md` 3 个：`wakita-subagent-create` / `wakita-audit` / `wakita-lock`（Codex 斜杠命令等价物，frontmatter 含 `description` + `argument-hint`）。
- 文档：新增 `docs/codex-子智能体方案.md`（诊断结论 + 使用指南）；`scripts/README.md` 加 Codex 章节；`AGENTS.md` + `README.md` 同步。
- `using-wakita` skill 加「Codex 环境调度」章节（@mention / spawn 调遣方式）。
- 修复 `inject-agent-model.py`：默认 provider key（DeepSeek `466f...`）在本机 config 已不存在，改为不存在时回退到第一个可用 provider。

## 技术要点 ★

### Codex 机制（官方文档依据）
- 自定义 agent：`~/.codex/agents/<name>.toml`（个人）或 `.codex/agents/`（项目级），独立 TOML 文件自动发现，无需在 config.toml 注册。来源：developers.openai.com/codex/subagents。
- 自定义提示词：`~/.codex/prompts/<cmd>.md`，YAML frontmatter `description`/`argument-hint`，正文为指令。来源：learn.chatgpt.com/docs/custom-prompts。**注意：官方已标记 deprecated，且仅在 Codex CLI / IDE 扩展中显示，桌面 App 不支持用户斜杠命令**。
- 插件 hooks：Codex 会加载插件自带的 `hooks/hooks.json`（「非托管 hooks」，用户信任后生效，`[hooks.state]` 记录信任哈希），并展开 `${CLAUDE_PLUGIN_ROOT}` / `${PLUGIN_ROOT}`。实测本机 PreToolUse/PostToolUse/UserPromptSubmit 均运行（插件缓存 audit.log 有实时记录）。
- 可选字段（缺省继承父会话）：`model`、`model_reasoning_effort`、`sandbox_mode`、`mcp_servers`、`skills.config`、`nickname_candidates`。

### 本机环境事实
- Codex 引擎：App 内置 0.148.0-alpha.9；`~/.codex/config.toml` 默认 `deepseek-v4-flash` + `model_reasoning_effort = "high"`。
- 可用模型：`deepseek-v4-flash` / `deepseek-v4-pro`（`~/.codex/models.json`）。
- ZCode config（`~/.zcode/v2/config.json`）中 DeepSeek `466f...` 已禁用/无 Key（不可用），可用的是 `opencode-go`（key `4ac42331-...`）→ 脚本默认 provider 需回退逻辑。

### 涉及文件
- 新增 `plugins/wakita-governance/templates/codex-agents/wakita-{scout,builder,auditor}.toml`
- 新增 `plugins/wakita-governance/templates/codex-prompts/wakita-{subagent-create,audit,lock}.md`
- 新增 `plugins/wakita-governance/scripts/inject-codex-agents.py`
- 新增 `docs/codex-子智能体方案.md`、`docs/specs/codex-subagent-support.md`
- 修改 `plugins/wakita-governance/scripts/inject-agent-model.py`（默认 provider 回退）
- 修改 `plugins/wakita-governance/scripts/README.md`、`skills/using-wakita/SKILL.md`
- 修改根 `README.md`、`AGENTS.md`；版本 2.4.0 → 2.5.0（4 处同步）

### 关键约束
- TOML 必须可被 tomllib 解析；prompt frontmatter 必须为合法 YAML。
- 不修改用户 `~/.codex/config.toml`（agent 自动发现，无需注册）。
- 脚本只写 `~/.codex/agents/` 与 `~/.codex/prompts/`，写前 `.bak`，重复运行跳过（幂等）。
- 角色正文与 ZCode 版保持同一事实源口径（结果回传协议不改）。
- hooks 在 Codex 下随插件 `hooks.json` 加载（信任后生效），无需另行配置；但需保证 `/wakita-audit`、`/wakita-lock` 读写**插件缓存副本**（与运行中的 hook 同目录），并修复 Windows 下 hook 输出的 GBK 乱码（4 个 hook 脚本统一 UTF-8）。

## 备选方案

| 方案 | 优势 | 劣势 | 落选原因 |
|------|------|------|----------|
| 直接把 MD 复制到 ~/.codex/agents/ | 零脚本 | Codex 不识别 MD agent 格式 | 不工作 |
| 只写文档、用户手建 | 无代码 | 易错、不可复用、无备份 | 可靠性差 |
| TOML 模板 + 注入脚本（选定） | 单一事实源、幂等、备份、可切模型 | 多一层脚本 | — |

## 影响范围

- governance 插件新增 codex-agents / codex-prompts 模板目录与一个脚本；文档与 skill 更新；版本号 4 处同步。
- hooks 脚本为两环境共用，v2.5.0 做了最小修复（4 个 hook 脚本强制 UTF-8、`audit.py` 补 CLI `main()`）；不改 ZCode 侧现有命令与模板、不影响 wakita-toolkit。

## 待确认

- [x] 版本号升 2.5.0（已按仓库规范同步 4 处）
- [x] 在本机执行 `--apply` 写入 `~/.codex/agents/` 与 `~/.codex/prompts/`（已验证）
