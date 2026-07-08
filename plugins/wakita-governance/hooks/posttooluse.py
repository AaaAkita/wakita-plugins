#!/usr/bin/env python3
"""PostToolUse hook —— 写操作留痕与提交规范检查。

在工具执行后调用。功能：
  - Edit/Write/Bash 写操作 → 写入 audit.log
  - git commit → 校验 message 是否中文（不符则提醒，不阻断）

协议：stdin 读 JSON，stdout 输出 JSON，必须 exit 0。
只做留痕和提醒，不阻断（阻断是 PreToolUse 的职责）。
"""

import json
import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from audit import append_audit
except ImportError as e:
    print(json.dumps({"systemMessage": f"[wakita] 审计模块加载失败：{e}"}))
    sys.exit(0)


# 中文字符范围（基本 + 扩展）
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def _has_chinese(text):
    """判断字符串是否含中文字符。"""
    return bool(_CJK_PATTERN.search(text or ""))


def _check_commit_message(command):
    """从 git commit 命令提取 message 并校验是否中文。

    支持 -m "msg" 和 -m 'msg' 和 -m msg 三种形式。
    返回提醒字符串或 None。
    """
    # 匹配 -m 后跟引号或裸文本
    m = re.search(r'-m\s+["\']([^"\']+)["\']', command)
    if not m:
        m = re.search(r'-m\s+(\S+)', command)
    if not m:
        return None  # 无 -m，可能是用编辑器写，跳过

    msg = m.group(1)
    if not _has_chinese(msg):
        return (
            f"⚠️ [wakita 规范] commit message 未检测到中文：\n  {msg}\n"
            "建议使用中文提交信息（参考 chinese-commit-messages skill）。"
        )
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    system_messages = []

    # —— 写操作留痕 ——
    if tool_name in ("Edit", "Write", "MultiEdit", "Bash"):
        summary = ""
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            if "git commit" in cmd:
                summary = "git-commit"
                # 额外校验 commit message
                warn = _check_commit_message(cmd)
                if warn:
                    system_messages.append(warn)
            elif cmd.startswith(("rm ", "mv ", "cp ", "mkdir ", "touch ")):
                summary = "fs-write"
        append_audit(tool_name, tool_input, summary)

    # —— 输出 ——
    if system_messages:
        output = {
            "systemMessage": "\n\n".join(system_messages),
        }
        print(json.dumps(output, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
