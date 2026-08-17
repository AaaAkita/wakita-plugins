---
description: 把文件加入 wakita 保护清单（rules.protected.json，与运行中的 PreToolUse hook 同目录）
argument-hint: <文件路径>
---

将指定文件加入 wakita-governance 的保护清单。步骤：

1. 定位**运行中的 hook 实际读取的清单位置**（PreToolUse hook 从插件缓存目录运行）：
   - 优先：`~/.codex/plugins/cache/wakita-plugins/wakita-governance/<版本>/hooks/`（取版本号最新目录；`rules.protected.json` 不存在会自动创建）
   - 回退：本仓库 `plugins/wakita-governance/hooks/`
2. 调用该 hooks 目录下的 rules.py 追加（把 `<文件路径>` 替换为用户传入的路径，PowerShell 下单引号包裹）：
   ```powershell
   python -c "import sys; sys.path.insert(0, r'<hooks目录>'); from rules import add_protected_file; print('已加锁' if add_protected_file(r'<文件路径>') else '该文件已在保护清单中')"
   ```
3. 返回"已加锁"后说明：
   - 保护清单内容为 `{"protected_files": [...]}`（被 .gitignore 排除，仅本地生效）；
   - Codex 加载插件 `hooks.json` 并信任后，PreToolUse 会真实拦截对该文件的后续 Edit/Write（见 `docs/codex-子智能体方案.md` 的「hooks 现状」）；若用户此前未信任插件 hooks，提示先完成信任流程；
   - 解锁需手动从清单中删除对应条目。
