#!/usr/bin/env python3
"""PostToolUse hook —— 分支合并复盘提醒。

检测 git merge 到 main/master，注入提醒询问是否整理可复用方案为 skill。

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
"""

import json
import re
import sys

# 检测"合并到主干"的模式：
# 1. git checkout main && git merge ...  → 明确先切到 main 再 merge
# 2. git merge <非main/master的branch>  → merge 的参数不是 main/master，说明正在合并 feature 到当前分支
_CHECKOUT_AND_MERGE = re.compile(
    r"\bgit\s+checkout\s+(?:main|master)\b.*\bgit\s+merge\b",
    re.IGNORECASE,
)
# merge 后面跟的不是 main/master（含 origin/main 等变体）
_MERGE_NOT_MAIN = re.compile(
    r"\bgit\s+merge\s+(?!origin/?(?:main|master)\b|main\b|master\b)\S+",
    re.IGNORECASE,
)

_MESSAGE = """\
[wakita] 检测到分支合并至主干——改动周期结束。

是否有可复用的方案值得泛化为 skill？
- 派 wakita-scout 扫描本次改动，提取可复用的模式/工具函数/组件
- 对照 code-reuse-audit 判断是否有重复逻辑可抽取
- 用 skill-creator 将稳定方案沉淀为新 skill

（无需处理请忽略，此提醒不会阻断任何操作）"""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # 两种模式任一命中即触发
    if _CHECKOUT_AND_MERGE.search(command) or _MERGE_NOT_MAIN.search(command):
        print(json.dumps({"systemMessage": _MESSAGE}, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
