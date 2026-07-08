---
description: 临时将文件加入 wakita 保护清单，禁止后续修改/删除
---

# /lock

将指定文件加入 wakita-governance 的保护清单。加入后，PreToolUse hook 会拦截对该文件的 Edit/Write 操作。

## 用法

```
/lock <文件路径>
```

## 实现

调用 rules.py 的 add_protected_file 函数追加保护项：

```bash
python -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/hooks'); from rules import add_protected_file; print('已加锁' if add_protected_file('$1') else '该文件已在保护清单中')"
```

将 `$1` 替换为用户传入的文件路径。

## 说明

- 保护清单存储在 `hooks/rules.protected.json`（被 .gitignore 排除，仅本地生效）。
- 默认保护文件见 `rules.py` 的 `DEFAULT_PROTECTED_FILES`（.env、lock 文件、.git 配置等）。
- 解锁需手动编辑 `rules.protected.json` 删除对应条目。

## 示例

```
/lock src/database/init.sql
```

执行后返回"已加锁"，之后任何 Edit/Write 该文件的操作都会被 PreToolUse 拦截。
