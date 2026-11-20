# 新增 wakita-ace 攻坚子智能体

**日期**: 2026-11-19
**状态**: 开发完成
**完成日期**: 2026-11-19

## 摘要

把已有的用户级 `wakita-ace`（高难度攻坚/扫地僧）纳入 wakita-governance 插件：新增 ZCode 模板 `templates/agents/wakita-ace.md` 与 Codex 模板 `templates/codex-agents/wakita-ace.toml`，两个注入脚本的 `AGENT_FILES` 各增加一项，`/subagent-create` 与 Codex 提示词、`using-wakita` 调度规范、README/AGENTS 文档同步从「三个 agent」改为「四个 agent」。版本 2.6.0 → 2.7.0。

## 背景与目标

- 问题：`wakita-ace` 目前只存在于本机 `~/.zcode/agents/`，属于手工文件；换机、重装、插件升级后无法复现，也不在 `/subagent-create` 的生成范围内。
- 目标：让 ace 与 scout/builder/auditor 同源管理——模板随插件分发，注入脚本统一渲染，Codex 侧有原生 TOML 等价物。
- 成功标准：`inject-agent-model.py` dry-run 的 `files` 出现 4 项；`inject-codex-agents.py --list` 出现 4 个 agent；新会话可调遣 `wakita-ace` / `@wakita-ace`。

## 方案

- 新增 ZCode 模板：frontmatter 含 `model:`（默认 deepseek-v4-pro）+ `thoughtLevel: max` + `injectAgentsMd: true`，工具白名单为只读集合（Read/Glob/Grep/Bash/TodoWrite），正文补充触发条件、证据链工作流、副作用评估与「结果回传协议」。
- 新增 Codex 模板：`sandbox_mode = "read-only"`、`model_reasoning_effort = "max"`，`developer_instructions` 与 ZCode 版同一口径。
- 脚本：两个 `AGENT_FILES` 列表各加一项，更新注释/帮助文本/restart_hint，渲染与校验逻辑不变（ace 模板同时含 `model:` 与 `thoughtLevel:`，满足 `render_agent` 前置条件）。
- 调度：`using-wakita` 增加 ace 触发条件（同一 Bug 修复 ≥2 次仍复现、根因不明、跨模块/并发/时序问题）与「ace 定位 → builder 修复 → auditor 复审」流程；明确 ace 不替代常规审查/实现。
- 子会话延续：`using-wakita` 增加强制规则——同一任务/阶段/角色用 `SendMessage` + 原 `agentId` 复用已有子会话，换阶段/换角色/会话失效才新开；UserPromptSubmit 规范补第 8 条。原因：重开子会话会丢失上下文缓存，ace 等贵模型成本尤其高。
- 版本：2.6.0 → 2.7.0，同步 plugin.json / kimi.plugin.json / marketplace.json / AGENTS.md + README.md。

## 技术要点 ★

### 涉及文件
- `plugins/wakita-governance/templates/agents/wakita-ace.md` — 新增 ZCode 模板
- `plugins/wakita-governance/templates/codex-agents/wakita-ace.toml` — 新增 Codex 模板
- `plugins/wakita-governance/scripts/inject-agent-model.py` — `AGENT_FILES` 加 `wakita-ace.md`
- `plugins/wakita-governance/scripts/inject-codex-agents.py` — `AGENT_FILES` 加 `wakita-ace.toml`，更新提示
- `plugins/wakita-governance/commands/subagent-create.md` — 三个 → 四个
- `plugins/wakita-governance/templates/codex-prompts/wakita-subagent-create.md` — 三个 → 四个
- `plugins/wakita-governance/skills/using-wakita/SKILL.md` — 角色表、攻坚升级章节、调度示例
- `plugins/wakita-governance/hooks/wakita-userpromptsubmit.py` — 规范第 6 条补 ace 升级提示
- `README.md` / `AGENTS.md` / `scripts/README.md` / `docs/codex-子智能体方案.md` — 数量与角色说明
- `.claude-plugin/marketplace.json` / `plugin.json` / `kimi.plugin.json` — 版本与描述

### 关键约束
- 模板文件名、agent `name` 统一小写 `wakita-ace`（与其余三个一致；本机旧文件 `name: "wakita-Ace"` 会在下次 `/subagent-create --apply` 时被覆盖并备份 `.bak`）
- ace 只读：不授予 Write/Edit；修复由 builder 执行
- ZCode 注入脚本的行为不变：一次 `--apply` 用同一 provider/model 渲染全部四个 agent；模板里的 pro 默认值只在未显式指定模型时作为意图声明
- 版本号必须同步 marketplace.json 的 description，ZCode 据此检测更新

## 备选方案

| 方案 | 优势 | 劣势 | 落选原因 |
|------|------|------|----------|
| 只保留用户级文件，不进插件 | 零改动 | 换机/升级丢失，无法复现 | 不符合仓库可复现目标 |
| 单独做成一个 skill | 不动 agent 体系 | 仍需手工生成 agent，调度割裂 | 不是 skill 场景 |
| 纳入现有模板 + 注入脚本（选定） | 单一事实源、双端（ZCode/Codex）一致 | 需同步多处文档与计数 | — |

## 影响范围

- 新增第 4 个子智能体，不影响 hooks 拦截规则
- 用户下次运行 `/subagent-create` 会生成/覆盖 `~/.zcode/agents/wakita-ace.md`（已备份 `.bak`）
- Codex 用户运行 `inject-codex-agents.py --apply` 后多出 `~/.codex/agents/wakita-ace.toml`

## 待确认

- [x] 模板 frontmatter 满足 `render_agent` 要求（`model:` + `thoughtLevel:` 均在 frontmatter 内）
- [x] Codex TOML 可被 `tomllib` 解析（已实测）
- [x] 两个脚本 dry-run 均列出 4 个文件
