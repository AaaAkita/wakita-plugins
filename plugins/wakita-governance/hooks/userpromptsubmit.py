#!/usr/bin/env python3
"""UserPromptSubmit hook —— 工作规范软提醒 + 场景提示。

每次用户提交 prompt 时注入轻量规范提示。不强制任何行为，仅作为上下文参考。

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
"""

import json
import sys

# 工作规范（始终注入，软提醒）
_NORMS = """\
[wakita 工作规范]
1. 提交信息（commit message）使用中文，类型前缀用英文。
2. 改动代码前先定位，结论带「文件:行号」证据。
3. 找不到证据明说"未找到"，不臆测。
4. 危险操作（rm -rf / 强推 / DROP 等）会被自动拦截。
5. 分支合并至主干后可复盘：有无可复用方案值得沉淀为 skill。
6. 接到代码改动需求时，按 using-wakita 技能分级再动手（小/中/大），禁止未经分级直接开干。"""

# 打包关键词 → 场景提示
_PACK_KEYWORDS = [
    "打包", "出包", "构建 exe", "build.py", "build.sh",
    "pyinstaller", "PyInstaller", "打一个 v", "发布版本",
    "打包成exe", "打包为exe",
]

_PACK_HINT = """\
[pyinstaller-packaging]
- packaging.json 存在 → 只确认版本号 + 临时变更
- 不存在 → 5 个默认值问题（回车跳过）
- 构建成功后自动写回 JSON"""


def _detect_context(prompt_text):
    if not prompt_text:
        return ""
    for kw in _PACK_KEYWORDS:
        if kw.lower() in prompt_text.lower():
            return _PACK_HINT
    return ""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    prompt = input_data.get("prompt", "") or input_data.get("text", "") or ""

    parts = [_NORMS]
    extra = _detect_context(prompt)
    if extra:
        parts.append(extra)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(parts),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
