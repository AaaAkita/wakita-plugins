---
description: 生成/切换 wakita 三个 Codex 子智能体（scout/builder/auditor）到 ~/.codex/agents/ 并安装命令提示词
argument-hint: [--model <模型>] [--reasoning <档位>] [--no-prompts]
---

执行 wakita 子智能体的 Codex 安装流程。步骤：

1. 定位仓库中的注入脚本（本仓库为 `plugins/wakita-governance/scripts/inject-codex-agents.py`；若不在 wakita-plugins 仓库，请先确认插件目录）。
2. 读取当前配置与模板默认值（只读，不落盘）：
   ```bash
   python plugins/wakita-governance/scripts/inject-codex-agents.py --json
   ```
3. 若用户传了 `--model` / `--reasoning` / `--no-prompts`，原样追加到后续命令。
4. 先跑 dry-run 向用户展示将要写入 `~/.codex/agents/` 与 `~/.codex/prompts/` 的文件及状态（missing / will_update / identical），征得确认后再执行：
   ```bash
   python plugins/wakita-governance/scripts/inject-codex-agents.py --apply
   ```
5. 成功后提示生效方式：
   - 新开会话（或重启 Codex App / 重开 CLI 会话）后，三个 agent 可用：`@wakita-scout`、`@wakita-builder`、`@wakita-auditor`；
   - 已安装的提示词在 CLI / IDE 扩展中以 `/wakita-subagent-create`、`/wakita-audit`、`/wakita-lock` 出现；⚠️ 官方已标记自定义提示词 deprecated，桌面 App 不显示，App 里直接让主智能体执行上述步骤即可；
   - 已有文件已备份为 `.bak`，回滚方法见 `docs/codex-子智能体方案.md`。

约束：只写入 `~/.codex/agents/` 与 `~/.codex/prompts/`，不修改 `~/.codex/config.toml`；不改动 ZCode 侧 `~/.zcode/agents/`。
