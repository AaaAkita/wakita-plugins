#!/usr/bin/env python3
"""UserPromptSubmit hook —— 工作规范注入。

每次用户提交 prompt 时注入系统提示，强化工作规范：
  - commit message 必须中文
  - 修改代码必须带文件:行号证据
  - 不臆测、找不到明说
  - 子智能体调用前必须先探索

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
注入用 hookSpecificOutput.additionalContext 字段。
"""

import json
import sys


# 注入的规范提示（保持精简，避免每次都灌入大段文字）
_NORMS = """\
[wakita 工作规范]
1. 提交信息（commit message）必须使用中文。
2. 改动代码前先定位，结论带「文件:行号」证据，不凭印象下判断。
3. 找不到证据就明说"未找到"，不要臆测"可能有"。
4. 调用子智能体前，先用 code-explorer 探索现有结构，再派 code-writer 实现。
5. 危险操作（rm -rf / 强推 / DROP 等）会被自动拦截，如需执行请先向用户确认。"""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # UserPromptSubmit 用 additionalContext 注入上下文
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _NORMS,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
