---
description: 查看最近的 wakita 审计日志
---

# /audit

查看 wakita-governance 记录的最近写操作与 git 提交日志。

## 用法

```
/audit [行数]
```

不传行数默认显示最近 50 条。

## 实现

执行以下命令读取审计日志：

```bash
python "${CLAUDE_PLUGIN_ROOT}/hooks/audit.py" read <行数>
```

由于 `audit.py` 默认是被 import 的，这里直接用 tail 读取：

```bash
tail -n {{行数或50}} "${CLAUDE_PLUGIN_ROOT}/hooks/audit.log" 2>/dev/null || echo "暂无审计记录"
```

将输出按时间倒序展示给用户，每条记录包含：
- 时间戳（ts）
- 工具名（tool）
- 操作摘要（summary）
- 文件路径或命令（path/command）
