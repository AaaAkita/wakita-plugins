#!/usr/bin/env python3
"""UserPromptSubmit hook —— 工作规范注入 + 场景检测。

每次用户提交 prompt 时注入系统提示。根据 prompt 内容动态追加场景提醒：
  - 始终注入：工作规范（commit 中文、带证据、不臆测、先探索）
  - 检测到打包关键词：追加 pyinstaller-packaging Q&A 提醒

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
"""

import json
import os
import sys

# 工作规范（始终注入）
_NORMS = """\
[wakita 工作规范]
1. 提交信息（commit message）必须使用中文。
2. 改动代码前先定位，结论带「文件:行号」证据，不凭印象下判断。
3. 找不到证据就明说"未找到"，不要臆测"可能有"。
4. 调用子智能体前，先用 wakita-scout 探索现有结构，再派 wakita-builder 实现。
5. 危险操作（rm -rf / 强推 / DROP 等）会被自动拦截，如需执行请先向用户确认。"""

# 打包关键词 → 触发 pyinstaller-packaging 提醒
_PACK_KEYWORDS = [
    "打包", "出包", "构建 exe", "build.py", "build.sh",
    "pyinstaller", "PyInstaller", "打一个 v", "发布版本",
    "打包成exe", "打包为exe", "--onefile", "--onedir",
]

_PACK_REMINDER = """\
[pyinstaller-packaging]
如需打包，按 Q&A 流程：
- packaging.json 存在 → 只问版本号 + 临时变更，其余静默沿用
- 不存在 → 问 5 个必要问题（有默认值，回车跳过）
- 构建成功后自动写回 JSON"""


def _detect_context(prompt_text):
    """根据 prompt 内容返回追加的场景提醒。"""
    if not prompt_text:
        return ""
    text_lower = prompt_text.lower()
    for kw in _PACK_KEYWORDS:
        if kw.lower() in text_lower:
            return _PACK_REMINDER
    return ""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # 抽取用户 prompt 文本
    prompt = input_data.get("prompt", "") or input_data.get("text", "") or ""

    # 拼接规范 + 场景提醒
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
