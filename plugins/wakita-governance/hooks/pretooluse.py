#!/usr/bin/env python3
"""PreToolUse hook —— 危险操作拦截。

在工具执行前调用。检查：
  - Bash 命令是否命中危险黑名单 → deny
  - Edit/Write 目标是否在保护清单 → deny
命中则输出 permissionDecision: deny 阻断；否则输出空 {} 放行。

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
任何异常都 exit 0 + systemMessage 告警，绝不阻塞正常工作。
"""

import json
import os
import sys

# 把 hooks 目录加入 path 以便 import rules
_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from rules import match_dangerous_command, is_path_protected, PROTECTED_FILE_MSG
except ImportError as e:
    # rules 导入失败：放行但告警，不阻塞
    print(json.dumps({"systemMessage": f"[wakita] 规则模块加载失败，拦截功能降级：{e}"}))
    sys.exit(0)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # 输入解析失败：放行，无法判断
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    hook_event = input_data.get("hook_event_name", "PreToolUse")

    deny_reason = None

    # —— Bash：检查危险命令 ——
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            deny_reason = match_dangerous_command(command)

    # —— Edit/Write/MultiEdit：检查保护文件 ——
    if not deny_reason and tool_name in ("Edit", "Write", "MultiEdit"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            protected = is_path_protected(file_path)
            if protected:
                deny_reason = PROTECTED_FILE_MSG.format(path=protected)

    # —— 输出 ——
    if deny_reason:
        # 阻断：PreToolUse 用 permissionDecision: deny
        output = {
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "permissionDecision": "deny",
            },
            "systemMessage": f"🛑 [wakita 拦截] {deny_reason}",
        }
        print(json.dumps(output, ensure_ascii=False))
    # else: 空输出放行（不 print 任何东西，或 print 空 dict）
    # 选择 print 空 dict 更明确
    # print("{}")

    sys.exit(0)


if __name__ == "__main__":
    main()
