---
description: 查看 wakita 审计日志（PostToolUse hook 写入插件缓存 hooks/audit.log）
argument-hint: [行数]
---

查看 wakita-governance 的审计日志。步骤：

1. 定位**运行中的 hook 实际写日志的位置**（PostToolUse hook 从插件缓存目录运行）：
   - 优先：`~/.codex/plugins/cache/wakita-plugins/wakita-governance/<版本>/hooks/audit.log`（取版本号最新目录）
   - 回退：本仓库 `plugins/wakita-governance/hooks/audit.log`（ZCode 会话或手工测试留下的数据）
2. 读取最近 N 条（不传默认 50）：
   ```powershell
   Get-Content <上面定位到的 audit.log> -Tail <行数>
   ```
   或 `python <hooks目录>/audit.py read <行数>`（v2.5.0 起 `audit.py` 已支持 `read` 子命令）。
3. 按时间倒序展示最近 N 条记录，每条含：时间戳、工具名、操作摘要、文件路径或命令。
4. **重要提示**：Codex 加载插件 `hooks.json` 并信任后，PostToolUse 留痕实时写入插件缓存（见 `docs/codex-子智能体方案.md` 的「hooks 现状」）。若日志不存在或为空，说明当前会话尚无写操作记录，或插件 hooks 尚未被信任——如实告知用户原因，不要编造记录。
